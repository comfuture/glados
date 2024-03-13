import os
import asyncio
from argparse import ArgumentParser
from dotenv import load_dotenv

load_dotenv()

from slack_bolt.adapter.socket_mode.websockets import AsyncSocketModeHandler  # noqa: E402
from glados.client.slack.bot import app  # noqa: E402


async def run_slackbot():
    """run slackbot"""
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--client", required=True, choices=["slack"], help="client to run"
    )
    args = parser.parse_args()
    client = args.client
    if client == "slack":
        asyncio.run(run_slackbot())
