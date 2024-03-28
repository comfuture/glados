import os
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

from slack_bolt.adapter.socket_mode.websockets import AsyncSocketModeHandler  # noqa: E402
from ipny.client.slack.bot import app  # noqa: E402


async def start():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(start())
