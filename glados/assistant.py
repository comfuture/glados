import os
import asyncio
from typing import Optional, AsyncGenerator
from enum import Enum
from openai import OpenAI
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from .session import SessionManager, Session
from .tool import invoke_tool_calls, choose_tools
from typing import TypedDict


class EventType(str, Enum):
    FUNCTION_CALLING = "function_calling"
    DRAWING_IMAGE = "drawing_image"


class AssistantResponse(TypedDict):
    event: EventType
    content: str | None


class GLaDOS:
    def __init__(self):
        self.client = OpenAI()
        self.session = None

    def resume_session(self, session_id: str):
        """Resume a session."""
        self.session = SessionManager.get_session(session_id)

    async def chat(
        self,
        message: Optional[str] = None,
        *,
        session_id: Optional[str] = None,
        image_urls: Optional[list[str]] = None,
        file_ids: Optional[list[str]] = None,
        tools: Optional[list[str]] = None,
    ) -> AsyncGenerator[str | AssistantResponse, None]:
        """Try to chat with the assistant.

        Args:
            message (str, optional): The message to send to the assistant. Defaults to None.
            session_id (str, optional): The ID of the session. Defaults to None.
            image_urls (list[str], optional): The list of image URLs to include in the conversation. Defaults to None.
            file_ids (list[str], optional): The list of file IDs to include in the conversation. Defaults to None.

        Yields:
            str: The assistant's responses.
        """

        if session_id:
            session = SessionManager.get_session(session_id)
        else:
            session = Session()

        session.model = os.environ.get("OPENAI_MODEL", "gpt-4-turbo-preview")
        if message:
            if image_urls and len(image_urls) > 0:
                context = "\n".join(f"- {image_url}" for image_url in image_urls)
                session(
                    f"{message}\n\nPlease response with refer to the image urls.\nImage URL:\n{context}"
                )
                # if message is provided, determine whether to use tools or not
            else:
                session(message)

            # if tools is not provided, choose tools from the message
            tools = await choose_tools(message)

        async def gen_answer():
            """Generate the assistant's answer.
            for the clients like Slack, generates answer line by line.
            """
            completion = session.invoke(self.client, stream=True, tools=tools)

            assistant_message = ""
            tool_calls: list[ChoiceDeltaToolCall] = []
            for chunk in completion:
                delta = chunk.choices[0].delta

                # collect partial tool calls message delta and reassemble them
                if delta.tool_calls:
                    for partial_tool_call in delta.tool_calls:
                        if partial_tool_call.id is not None:
                            # Extend tool_calls list if necessary
                            while len(tool_calls) <= partial_tool_call.index:
                                tool_calls.append(None)

                            tool_calls[partial_tool_call.index] = partial_tool_call
                        if partial_tool_call.function.name is not None:
                            tool_calls[
                                partial_tool_call.index
                            ].function.name = partial_tool_call.function.name
                        if partial_tool_call.function.arguments is not None:
                            tool_calls[
                                partial_tool_call.index
                            ].function.arguments += partial_tool_call.function.arguments

                # append content to assistant message
                if delta.content:
                    assistant_message += delta.content
                    yield delta.content

                if chunk.choices[0].finish_reason == "tool_calls":
                    # append tool calls message to session
                    m = {
                        "tool_calls": [c.dict() for c in tool_calls if c is not None],
                    }
                    session(m, role="assistant")

                    # show tool calls information to ui
                    tool_names = [f.function.name for f in tool_calls]
                    yield AssistantResponse(
                        event=EventType.FUNCTION_CALLING,
                        content=",".join(tool_names),
                    )

                    # call tools and append the result to session
                    calls = await invoke_tool_calls(tool_calls)
                    for tool_message in calls:
                        session(tool_message)
                    tool_calls = []

                    # finally send the tool calls result to client and stream the result
                    async for answer in gen_answer():
                        yield answer
                    return

            # at the end of the conversation, save entire assistant message to session
            if assistant_message:
                session(assistant_message, role="assistant")

        async for answer in gen_answer():
            yield answer

    async def natural_delay_generator(self, source: str) -> AsyncGenerator[str, None]:
        """Generate a natural delay between lines."""
        for line in source.split("\n"):
            delay = len(line) * 0.02
            yield asyncio.sleep(delay, line)
