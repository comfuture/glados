import os
import re
import json
import asyncio
import tempfile
from typing_extensions import override
import time
from datetime import datetime
from io import BytesIO
import requests
import pytz
from slack_bolt.async_app import AsyncApp

from openai.types.beta.threads.message_content import (
    MessageContent,
    TextContentBlock,
    ImageFileContentBlock,
)
from openai.types.beta.threads.message_content_delta import (
    TextDeltaBlock,
)
from openai.types.beta.threads.annotation import (
    FilePathAnnotation,
    FileCitationAnnotation,
)
from ...assistant import (
    GLaDOS,
    AsyncAssistantEventHandler,
)
from ...tool import invoke_function, get_tool_meta
from ...session import SessionManager, Session
from ...util import is_image_url, make_public_url
from ...util.file import upload_files
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


@app.event("app_mention")
@app.event("message")
async def handle_message_events(ack, client, body, event, say, context):
    """Handle a message."""
    await ack()

    # prevent the bot from replying to non-existing channels
    if not event.get("channel"):
        return

    if "user" not in event:  # if message event was not sent by a user,
        return
    if (
        event["type"] != "message"
    ):  # if message event is not a message caused by unknown reason,
        return

    prompt: str | list = event.get("text", "")

    is_direct_message = event["channel_type"] == "im" or event["channel_type"] == "mpim"
    is_mentioned = f"<@{app.bot_user_id}>" in prompt

    if is_mentioned:
        # if mentioned, treat as a new conversation
        session_id = event.get("thread_ts", event.get("ts"))
        prompt = re.sub(
            re.compile(rf"<@{app.bot_user_id}>", re.IGNORECASE), "", prompt
        ).strip()
    elif is_direct_message:
        if not event.get("thread_ts"):  # first message in a direct message
            session_id = event.get("ts")
        else:
            session_id = event.get("thread_ts")
    else:
        # if message is from a thread, thread_id is set
        session_id = event.get("thread_ts")

    if not session_id:
        # if not in a thread, treat as a new conversation
        return

    is_bot_thread = await SessionManager.has_session(session_id)

    # no need to reply on other user's thread. quit
    if not is_bot_thread and not is_mentioned and not is_direct_message:
        return

    content_blocks = []
    to_uploaded = []
    attachments = []
    if "files" in event:
        for file in event["files"]:
            if file.get("mimetype", "").startswith("image/"):
                await say(
                    "Looking at the image...",
                    blocks=[
                        b.Context(":frame_with_picture: 이미지를 살펴보고 있습니다...")
                    ],
                    thread_ts=session_id,
                )
                response = requests.get(
                    file["url_private"],
                    headers={"Authorization": f"Bearer {app.client.token}"},
                )
                image_file = await assistant.client.files.create(
                    file=(file["name"], BytesIO(response.content), file["mimetype"]),
                    purpose="assistants",
                )
                content_blocks.append(
                    {
                        "type": "image_file",
                        "image_file": {"file_id": image_file.id},
                    }
                )
            elif file.get("mimetype", "").startswith("audio/"):
                response = requests.get(
                    file["url_private_download"],
                    headers={"Authorization": f"Bearer {app.client.token}"},
                    allow_redirects=True,
                )

                # XXX: use a temporary file because BytesIO doesn't work here
                with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
                    with open(tmp.name, "wb+") as f:
                        await say(
                            "Transcribing audio...",
                            blocks=[b.Context(":speech_balloon: 소리를 듣는 중입니다")],
                            thread_ts=session_id,
                        )
                        f.write(response.content)
                        f.seek(0)
                        transcript = await assistant.client.audio.transcriptions.create(
                            model="whisper-1", file=f
                        )
                        print(f"{transcript.text=}")
                        content_blocks.append(
                            {
                                "type": "text",
                                "text": f"Transcripted from audio:\n{transcript.text}",
                            }
                        )
            else:
                file_content = download_slack_file(file["url_private_download"])
                to_uploaded.append((file["name"], file_content, file["mimetype"]))
            attachments = await upload_files(to_uploaded)

    if not prompt and len(content_blocks) == 0:
        return

    print(f"<@{event['user']}> {prompt}")

    # extract image url from prompt
    url_re = re.compile(r"(https?://\S+)")
    inline_url = re.search(url_re, prompt)
    if inline_url and is_image_url(inline_url.group(1)):
        image_url = inline_url.group(1)
        content_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            }
        )
        prompt = re.sub(re.compile(rf"<?{re.escape(image_url)}([^>*]>?), "), prompt)

    if len(content_blocks) > 0:
        if prompt:
            content_blocks.append(
                {
                    "type": "text",
                    "text": prompt,
                }
            )
            del prompt
        prompt = content_blocks[:]

    # fill current context
    info = await client.users_info(user=event["user"])
    session = await SessionManager.get_session(session_id, user=event["user"])
    user_tz = info["user"].get("tz", "UTC")
    current_date = pytz.timezone(user_tz).localize(datetime.fromtimestamp(time.time()))
    session.context.set(
        {
            "platform": "slack",
            "current_date": current_date.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "user": event["user"],
            "display_name": info["user"].get("name", {}),
            "timezone": user_tz,
            "channel": event["channel"],
        }
    )

    handler = SlackMessageHandler(
        client, say, session=session, thread_ts=session_id, channel=event.get("channel")
    )
    await assistant.chat(
        prompt,
        handler=handler,
        attachments=attachments,
        session_id=session_id,
    )


file_info_cache = {}


async def get_file_info(file_id: str):
    """
    Retrieves information about a file given its ID.
    """
    if file_id in file_info_cache:
        return file_info_cache[file_id]
    file_info = await assistant.client.files.retrieve(file_id)
    file_info_cache[file_id] = file_info
    return file_info


class SlackMessageHandler(AsyncAssistantEventHandler):
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
        self.tool_outputs = []
        self.citations = {}

    def clone(self):
        """Clone the current handler."""
        return SlackMessageHandler(
            self.client,
            self.say,
            session=self.session,
            thread_ts=self.thread_ts,
            channel=self.channel,
        )

    async def process_annotation(self, message_content: MessageContent):
        """Process the annotations in the message content."""
        if hasattr(message_content.text, "annotations"):
            for annotation in message_content.text.annotations:
                if isinstance(annotation, FilePathAnnotation):
                    replacer = annotation.text
                    file_id = annotation.file_path.file_id
                    file_content = await assistant.client.files.content(file_id)
                    r = await self.client.files_upload_v2(
                        title="File",
                        content=file_content.read(),
                        channel=self.channel,
                        thread_ts=self.thread_ts,
                    )
                    new_text = message_content.text.value.replace(
                        replacer, r["file"]["permalink"]
                    )
                    message_content.text.value = new_text
                if isinstance(annotation, FileCitationAnnotation):
                    replacer = annotation.text
                    file_id = annotation.file_citation.file_id
                    file_info = await get_file_info(file_id)
                    new_text = message_content.text.value.replace(replacer, "")
                    message_content.text.value = new_text
                    self.citations[file_id] = file_info
        return message_content

    @override
    async def on_message_created(self, message):
        """When a message is created, start a new message with the assistant's response."""
        r = await self.say(
            "Thinking...",
            thread_ts=self.thread_ts,
            blocks=[b.Context(":hourglass_flowing_sand: Thinking...")],
        )
        self.message_ts = r.get("ts")

    @override
    async def on_message_delta(self, delta, snapshot):
        for content in delta.content:
            if isinstance(content, TextDeltaBlock):
                # flush every line if the delta contains newlines
                if "\n" in (content.text.value or ""):
                    if isinstance(snapshot.content[0], TextContentBlock):
                        to_say, _, remain = snapshot.content[0].text.value.rpartition(
                            "\n"
                        )
                        await self.client.chat_update(
                            channel=self.channel,
                            ts=self.message_ts,
                            text=to_say,
                            blocks=list(format_response(to_say)),
                        )
                    elif isinstance(snapshot.content[0], ImageFileContentBlock):
                        ...
            else:
                # print(f"implement this: {delta=}, {snapshot=}")
                ...

    @override
    async def on_message_done(self, message):
        """Update the entire message with the response."""
        # TODO: append action buttons block to the message
        for content in message.content:
            if isinstance(content, TextContentBlock):
                content = await self.process_annotation(content)
                await self.client.chat_update(
                    channel=self.channel,
                    ts=self.message_ts,
                    text=content.text.value,
                    blocks=list(format_response(content.text.value)),
                )
            elif isinstance(content, ImageFileContentBlock):
                image_content = await assistant.client.files.content(
                    content.image_file.file_id
                )
                await self.client.files_upload_v2(
                    title="Image file",
                    filetype="png",
                    content=image_content.read(),
                    channel=self.channel,
                    thread_ts=self.thread_ts,
                )

        # add citations info below
        if len(self.citations):
            await self.say(
                attachments=[
                    {
                        "title": "References",
                        "fields": [
                            {
                                "title": file_info.filename,
                                "value": f"{file_info.bytes} bytes",
                            }
                            for file_info in self.citations.values()
                        ],
                        "color": "#36a64f",
                    }
                ],
                thread_ts=self.thread_ts,
            )
            self.citations = {}

    @override
    async def on_image_file_done(self, image_file):
        """When an image file created by the assistant, upload it to Slack and show it."""
        # TODO: upload to slack?
        # image_content = await assistant.client.files.retrieve_content(
        #     image_file.file_id
        # )
        # await self.client.files_upload(
        #     title="Image file",
        #     filename="image.png",
        #     content=image_content,
        #     channel=self.channel,
        #     thread_ts=self.thread_ts,
        # )

    @override
    async def on_tool_call_created(self, tool_call):
        """When a tool call is created, show the tool call type and icon."""
        # show tool call type and icon
        if tool_call.type == "function":
            # get icon
            meta = get_tool_meta(tool_call.function.name)
            await self.say(
                f"Using {meta.get('name')}",
                blocks=[b.Context(f"Using {meta.get('icon')} {meta.get('name')}")],
                thread_ts=self.thread_ts,
            )
        elif tool_call.type == "code_interpreter":
            await self.say(
                "Running code...",
                blocks=[b.Context(":keyboard: 코드를 실행하고 있습니다...")],
                thread_ts=self.thread_ts,
            )
        elif tool_call.type == "file_search":
            await self.say(
                "Searching files...",
                blocks=[b.Context(":mag: 파일을 검색하고 있습니다...")],
                thread_ts=self.thread_ts,
            )

    @override
    async def on_run_step_created(self, run_step):
        """Each time a run step is created, update the run ID."""
        self.run_id = run_step.run_id

    @override
    async def on_end(self) -> None:
        # after the stream ends, check if the run requires action
        run = await assistant.client.beta.threads.runs.retrieve(
            self.run_id, thread_id=self.session.thread_id
        )
        if (
            run.status == "requires_action"
            and run.required_action.type == "submit_tool_outputs"
        ):
            # if needed, submit the tool outputs and continue with cloned handler
            async with assistant.client.beta.threads.runs.submit_tool_outputs_stream(
                run_id=self.run_id,
                thread_id=self.session.thread_id,
                tool_outputs=self.tool_outputs,
                event_handler=self.clone(),  # because the event handler can not be reused
            ) as stream:
                await stream.until_done()

    @override
    async def on_tool_call_done(self, tool_call):
        """When a tool call delta is done, inject the result to the conversation
        and continue with the submitted tool outputs."""
        if tool_call.type == "function":
            kwargs = json.loads(tool_call.function.arguments)
            result = await invoke_function(tool_call.function.name, **kwargs)

            self.tool_outputs.append({"tool_call_id": tool_call.id, "output": result})

        elif tool_call.type == "code_interpreter":
            # TODO: implement this ?
            # await self.client.files_upload_v2(
            #     title="Code",
            #     filetype="python",
            #     content=tool_call.code_interpreter.input,
            #     channel=self.channel,
            #     thread_ts=self.thread_ts,
            # )
            ...
