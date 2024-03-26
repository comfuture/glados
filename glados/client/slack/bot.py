import os
import re
import json
import asyncio
import tempfile
from typing import Callable, Any, AsyncGenerator
from typing_extensions import override
import time
from datetime import datetime
from io import BytesIO
import requests
import pytz
from slack_bolt.async_app import AsyncApp

from ...assistant import (
    GLaDOS,
    AssistantResponse,
    AsyncAssistantEventHandler,
)
from ...tool import invoke_function, get_tool_meta
from ...session import SessionManager, Session
from ...util import is_image_url, make_public_url
from .formatter import block as b, format_response


class SlackBot(AsyncApp):
    def __init__(self, token: str, signing_secret: str):
        self.bot_user_id = None

        super().__init__(token=token, signing_secret=signing_secret)

        async def get_auth_result():
            auth = await self.client.auth_test()
            self.bot_user_id = auth["user_id"]

        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_auth_result())


app = SlackBot(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

assistant = GLaDOS()


def download_slack_file(url: str) -> BytesIO:
    """Download a file from Slack."""
    r = requests.get(url, headers={"Authorization": f"Bearer {app.client.token}"})
    r.raise_for_status()
    return BytesIO(r.content)


async def line_iterator(source: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """Iterate over lines of a string or an async generator."""
    buffer = ""
    async for chunk in source:
        if isinstance(chunk, dict):
            yield chunk
            continue
        buffer += chunk
        if "\n" in chunk:
            line, buffer = buffer.split("\n", 1)
            yield line
    if buffer:
        yield buffer


async def stream_to_transport(
    source: str | AsyncGenerator[str | AssistantResponse, None],
    send_func: Callable[[str], Any],
    channel: str | None = None,
    thread_ts: str | None = None,
):
    """Stream the response to the bot transport."""
    block_ts: str | None = None
    block_content = ""

    async for line in source:
        if isinstance(line, dict):
            await send_func(
                blocks=[b.Context(f":information_source: Using {line['content']}")],
                text=f"* Using {line['content']}",
                thread_ts=thread_ts,
            )
            block_ts = None
            block_content = ""
            continue
        block_content += line + "\n"
        if not block_ts:
            r = await send_func(
                text=block_content,
                blocks=list(format_response(line)),
                thread_ts=thread_ts,
            )
            block_ts = r.get("ts")
        else:
            await app.client.chat_update(
                channel=channel,
                ts=block_ts,
                thread_ts=thread_ts,
                text=block_content,
                blocks=list(format_response(block_content)),
            )


@app.event("app_mention")
@app.event("message")
async def handle_message_events(ack, client, body, event, say, context):
    """Handle a message."""
    await ack()

    # if message is from a thread, thread_id is set
    session_id = event.get("thread_ts")

    if "user" not in event:  # if message event was not sent by a user,
        return
    if (
        event["type"] != "message"
    ):  # if message event is not a message caused by unknown reason,
        return

    prompt = event.get("text", "")

    is_direct_message = event["channel_type"] == "im" or event["channel_type"] == "mpim"
    is_mentioned = f"<@{app.bot_user_id}>" in prompt

    prompt = re.sub(
        re.compile(rf"<@{app.bot_user_id}>", re.IGNORECASE), "", prompt
    ).strip()

    if is_mentioned:
        # if mentioned, treat as a new conversation
        session_id = event.get("ts")

    if is_direct_message:
        # in a direct message, all messages are in the same thread
        session_id = event.get("user")

    if not session_id:
        # if not in a thread, treat as a new conversation
        return

    image_urls = []

    if "files" in event:
        for file in event["files"]:
            if file.get("mimetype", "").startswith("image/"):
                await say(
                    blocks=[
                        b.Context(":frame_with_picture: 이미지를 살펴보고 있습니다...")
                    ],
                    thread_ts=None if is_direct_message else session_id,
                )
                response = requests.get(
                    file["url_private"],
                    headers={"Authorization": f"Bearer {app.client.token}"},
                )
                image_url = make_public_url(
                    BytesIO(response.content), ext=file["filetype"]
                )
                image_urls.append(image_url)
            if file.get("mimetype", "").startswith("audio/"):
                response = requests.get(
                    file["url_private_download"],
                    headers={"Authorization": f"Bearer {app.client.token}"},
                    allow_redirects=True,
                )

                # XXX: use a temporary file because BytesIO doesn't work here
                with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
                    with open(tmp.name, "wb+") as f:
                        f.write(response.content)
                        f.seek(0)
                        transcript = assistant.client.audio.transcriptions.create(
                            model="whisper-1", file=f
                        )
                        await say(
                            blocks=[b.Context(f":speech_balloon: {transcript.text}")]
                        )
                        prompt += "\n\n" + transcript.text

    if not prompt:
        return

    # extract image url from prompt
    url_re = re.compile(r"(https?://\S+)")
    inline_url = re.search(url_re, prompt)
    if inline_url and is_image_url(inline_url.group(1)):
        image_url = inline_url.group(1)
        image_urls.append(image_url)
        prompt = re.sub(re.compile(rf"<?{re.escape(image_url)}([^>*]>?), "), prompt)
        await say(
            blocks=[b.Context(":frame_with_picture: 이미지를 살펴보고 있습니다...")]
        )

    print(f"<@{event['user']}> {prompt}")

    # fill current context
    info = await client.users_info(user=event["user"])
    session = SessionManager.get_session(session_id)
    timezone = info["user"].get("tz", "UTC")
    current_date = pytz.timezone(timezone).localize(datetime.fromtimestamp(time.time()))
    session.context.set(
        {
            "platform": "slack",
            "current_date": current_date.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "user": event["user"],
            "display_name": info["user"].get("name", {}),
            "timezone": timezone,
            "channel": event["channel"],
        }
    )

    pipe = SlackTransport(
        client, say, session=session, thread_ts=session_id, channel=event.get("channel")
    )
    await assistant.chat(
        prompt,
        handler=pipe,
        image_urls=image_urls,
        session_id=session_id,
    )


class SlackTransport(AsyncAssistantEventHandler):
    """Assistant event handler for Slack."""

    def __init__(
        self,
        client,
        say,
        *,
        session: Session,
        thread_ts: str = None,
        message_ts: str = None,
        channel: str = None,
    ):
        super().__init__()
        self.client = client
        self.say = say
        self.session = session
        self.thread_ts = thread_ts
        self.message_ts = message_ts
        self.channel = channel

    def clone(self):
        """Clone the current handler."""
        return SlackTransport(
            self.client,
            self.say,
            session=self.session,
            thread_ts=self.thread_ts,
            channel=self.channel,
        )

    @override
    async def on_message_created(self, message):
        """When a message is created, start a new message with the assistant's response."""
        r = await self.say(
            "`...`",
            thread_ts=self.thread_ts,
            blocks=[b.Context(":hourglass_flowing_sand: 대답을 기다리는 중...")],
        )
        self.message_ts = r.get("ts")

    @override
    async def on_message_delta(self, delta, snapshot):
        content = delta.content[0]
        if content.type == "text":
            # flush every line if the delta contains newlines
            if "\n" in delta.content[0].text.value:
                to_say, _, remain = snapshot.content[0].text.value.rpartition("\n")
                await self.client.chat_update(
                    channel=self.channel,
                    ts=self.message_ts,
                    text=to_say,
                    blocks=list(format_response(to_say)),
                )
        else:
            print(f"implement this: {delta=}, {snapshot=}")

    @override
    async def on_message_done(self, message):
        """Update the entire message with the response."""
        # TODO: append action buttons block to the message
        await self.client.chat_update(
            channel=self.channel,
            ts=self.message_ts,
            text=message.content[0].text.value,
            blocks=list(format_response(message.content[0].text.value)),
        )

    @override
    async def on_image_file_done(self, image_file):
        """When an image file created by the assistant, upload it to Slack and show it."""
        # TODO: implement this properly
        image_content = await assistant.client.files.retrieve_content(
            image_file.file_id
        )
        new_file = await self.client.files_upload_v2(
            title="Image file",
            filename="image.png",
            content=image_content,
        )
        file_url = new_file.get("file").get("permalink")
        await self.say(
            blocks=[b.Image(file_url, "Image file")],
            thread_ts=self.thread_ts,
        )

    @override
    async def on_tool_call_created(self, tool_call):
        """When a tool call is created, show the tool call type and icon."""
        # show tool call type and icon
        if tool_call.type == "function":
            # get icon
            meta = get_tool_meta(tool_call.function.name)
            await self.say(
                blocks=[b.Context(f"Using {meta.get('icon')} {meta.get('name')}")],
                thread_ts=self.thread_ts,
            )

    @override
    async def on_run_step_created(self, run_step):
        """Each time a run step is created, update the run ID."""
        self.run_id = run_step.run_id

    @override
    async def on_tool_call_done(self, tool_call):
        """When a tool call delta is done, inject the result to the conversation
        and continue with the submitted tool outputs."""
        if tool_call.type == "function":
            kwargs = json.loads(tool_call.function.arguments)
            result = await invoke_function(tool_call.function.name, **kwargs)
            async with assistant.client.beta.threads.runs.submit_tool_outputs_stream(
                run_id=self.run_id,
                thread_id=self.session.thread_id,
                tool_outputs=[{"tool_call_id": tool_call.id, "output": result}],
                event_handler=self.clone(),
            ) as stream:
                await stream.until_done()

        elif tool_call.type == "code_interpreter":
            # TODO: implement this ?
            ...
