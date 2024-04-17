import os
from typing import Optional
from openai import (
    AsyncAssistantEventHandler,
    AsyncOpenAI,
)
from .backend.db import use_db
from .session import SessionManager
from .tool import choose_tools


class Ipny:
    """An assistant that uses the beta assistant API."""

    def __init__(self):
        self.client = AsyncOpenAI()
        self.assistant_id = os.environ.get("IPNY_ASSISTANT_ID")

    async def chat(
        self,
        message: str,
        *,
        handler: AsyncAssistantEventHandler,
        session_id: str,
        file_ids: Optional[list[str]] = [],
        image_urls: Optional[list[str]] = None,
        video_urls: Optional[list[str]] = None,
        tools: Optional[list[str]] = [],
    ) -> None:
        """Try to chat with the assistant.

        Args:
            message (str): The message to send to the assistant.
            handler (AsyncAssistantEventHandler): The event handler.
            session_id (str): The ID of the session.
            file_ids (list[str], optional): The list of file IDs to include in the conversation. Defaults to None.
            image_urls (list[str], optional): The list of image URLs to include in the conversation. Defaults to None.
            tools (list[str], optional): The list of tools to use. Defaults to [].
        """
        session = await SessionManager.get_session(session_id)
        SessionManager.current = session

        functions = await choose_tools(message)
        if functions:
            tools.extend(functions)

        if file_ids and len(file_ids) > 0:
            # append {'type': 'interpreter'} to tools deduped
            tools.append({"type": "code_interpreter"})

        if (
            not session.thread_id
        ):  # if session.thread_id is not set, create a new thread
            thread = await self.client.beta.threads.create()
            session.thread_id = thread.id
            db = use_db()
            col = db.get_collection("sessions")
            await col.update_one(
                {"session_id": session.id},
                {"$set": {"thread_id": session.thread_id}},
            )

        if image_urls and len(image_urls) > 0:
            urls = "\n".join(f"- {image_url}" for image_url in image_urls)
            message = f"Image URLs:\n{urls}\n{message}"

        if video_urls and len(video_urls) > 0:
            urls = "\n".join(f"- {video_url}" for video_url in video_urls)
            message = f"Video URLs:\n{urls}\n{message}"

        session(message)
        await self.client.beta.threads.messages.create(
            thread_id=session.thread_id, role="user", content=message, file_ids=file_ids
        )

        async with self.client.beta.threads.runs.create_and_stream(
            thread_id=session.thread_id,
            assistant_id=self.assistant_id,
            tools=tools,
            event_handler=handler,
        ) as stream:
            await stream.until_done()
