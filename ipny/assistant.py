import os
from typing import Optional, TypedDict
from enum import Enum
from openai import (
    AsyncAssistantEventHandler,
    AsyncOpenAI,
)
from openai.types.beta.threads.message_create_params import (
    Attachment,
    MessageContentPartParam,
)
from .backend.db import use_db
from .session import SessionManager
from .tool import choose_tools


class EventType(str, Enum):
    FUNCTION_CALLING = "function_calling"
    DRAWING_IMAGE = "drawing_image"


class AssistantResponse(TypedDict):
    event: EventType
    content: str | None


class Ipny:
    """An assistant that uses the beta assistant API."""

    def __init__(self):
        self.client = AsyncOpenAI()
        self.assistant_id = os.environ.get("IPNY_ASSISTANT_ID")

    async def chat(
        self,
        message: str | MessageContentPartParam,
        *,
        handler: AsyncAssistantEventHandler,
        session_id: str,
        attachments: Optional[list[Attachment]] = None,
        tools: Optional[list[str]] = [],
    ) -> None:
        """Try to chat with the assistant.

        Args:
            message (str): The message to send to the assistant.
            handler (AsyncAssistantEventHandler): The event handler.
            session_id (str): The ID of the session.
            attachments (list[Attachment], optional): The list of attachments to include in the conversation. Defaults to None.
            tools (list[str], optional): The list of tools to use. Defaults to [].
        """
        need_to_save = False
        session = await SessionManager.get_session(session_id)
        SessionManager.current = session

        functions = await choose_tools(message)
        if functions:
            tools.extend(functions)

        if (
            not session.thread_id
        ):  # if session.thread_id is not set, create a new thread
            thread = await self.client.beta.threads.create()
            session.thread_id = thread.id
            need_to_save = True

        session(message)

        if need_to_save:
            await SessionManager.save_session(session_id)

        await self.client.beta.threads.messages.create(
            thread_id=session.thread_id,
            role="user",
            content=message,
            attachments=attachments,
        )

        async with self.client.beta.threads.runs.stream(
            thread_id=session.thread_id,
            assistant_id=self.assistant_id,
            tools=tools,
            event_handler=handler,
        ) as stream:
            await stream.until_done()
