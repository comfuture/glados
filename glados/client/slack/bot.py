import os
import re
import asyncio
import tempfile
from typing import Callable, Any, AsyncGenerator, cast
from io import BytesIO
import requests
from slack_bolt.async_app import AsyncApp

from ...assistant import GLaDOS, EventType, AssistantResponse
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
async def handle_message_events(ack, body, event, say, context):
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
    # is_mentioned = f"<@{app.client.bot_user_id}>" in prompt
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
        print("no need to answer, quit")
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

    await stream_to_transport(
        line_iterator(
            assistant.chat(
                prompt,
                image_urls=image_urls,
                session_id=session_id,
            )
        ),
        say,
        channel=event.get("channel"),
        thread_ts=None if is_direct_message else session_id,
    )
