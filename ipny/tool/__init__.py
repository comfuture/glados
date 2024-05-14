import os
import glob
import importlib.util
import inspect
import json
from typing import Optional, TypedDict, Callable
from contextvars import ContextVar
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from function_schema import get_function_schema
from ..assistant import AsyncOpenAI
from ..session import Session

__registry__ = {}
context = ContextVar("session")


class PluginMeta(TypedDict):
    name: Optional[str]
    icon: Optional[str]


def plugin(fn: Optional[Callable] = None, **meta: PluginMeta):
    """Decorator to mark a function as a plugin."""

    if not fn or not callable(fn):
        return lambda fn: plugin(fn, **meta)

    __registry__[fn.__name__] = {
        "function": fn,
        "meta": meta,
        "schema": get_function_schema(fn),
    }
    print(f"Registerd tool {fn.__name__}")

    return fn


# Load all tools
current_dir = os.path.dirname(os.path.realpath(__file__))
py_files = glob.glob(os.path.join(current_dir, "*.py"))

for py_file in py_files:
    # Skip if the file is the current file
    if py_file == __file__:
        continue

    module_name = os.path.splitext(os.path.basename(py_file))[0]
    # Skip if the module name starts with '_'
    if module_name.startswith("_"):
        continue
    module_path = os.path.abspath(py_file)  # Get the absolute path of the module

    spec = importlib.util.spec_from_file_location(
        module_name, module_path
    )  # Use the absolute path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


async def noop(**kwargs):
    """Do nothing."""
    pass


def get_tool_meta(tool_name: str) -> PluginMeta:
    """Get the meta data of a tool."""
    tool = __registry__.get(tool_name, {"meta": {"name": tool_name, "icon": "🔧"}})

    return tool["meta"]


async def invoke_function(function_name: str, **kwargs):
    """Invoke a tool function.

    even if the function is not found, it should not raise an error, but return a message that the function is not found.
    if the function is corountine, it automatically awaits it.
    """
    tool = __registry__.get(function_name, {"function": noop})
    if inspect.iscoroutinefunction(tool["function"]):
        ret = await tool["function"](**kwargs)
    else:
        ret = tool["function"](**kwargs)
    return json.dumps(ret)


async def invoke_tool_calls(tool_calls: list[ChoiceDeltaToolCall]):
    """Invoke tool functions by tool_calls messages."""
    messages = []

    # to make things simple, call functions one by one now.
    # TODO: make it parallel
    for tool_call in tool_calls:
        assert tool_call.type == "function"
        tool_call_id = tool_call.id
        function = tool_call.function
        function_name = function.name
        try:
            kwargs = json.loads(function.arguments)
        except Exception:
            kwargs = {}
        try:
            result = await invoke_function(function_name, **kwargs)
            print(f"invoke {result=}")
        except Exception as e:
            result = "Error: " + str(
                e
            )  # don't raise an error, but return a message when something goes wrong
            print(f"error {result=}")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": result,
            }
        )
    return messages


def format_tools(tool_names: list[str]) -> list[dict] | None:
    """Format tool names as chat completion tools parameter."""
    if len(tool_names) == 0:
        return None

    def get_tool(tool_name):
        if tool_name in ("code_interpreter", "file_search"):
            return {"type": tool_name}
        tool = __registry__.get(tool_name)
        if tool is None:
            return None
        return {"type": "function", "function": tool["schema"]}

    return [get_tool(tool_name) for tool_name in set(tool_names)]


async def choose_tools(message: str) -> list[dict] | None:
    """automatically choose tools from a message."""

    # temporarily disable choosing tools
    return None

    ai = AsyncOpenAI()
    tool_names = "\n".join(
        [
            f"- {tool_name}: {impl['schema'].get('description', tool_name)}"
            for tool_name, impl in __registry__.items()
        ]
    )
    tool_names += (
        "\n- file_search: Search and query from files for accurate information."
    )
    tool_names += "\n- code_interpreter: Create and run python code. also can process files, evaluate math expressions, etc."

    s = Session(model="gpt-3.5-turbo")
    s("Output JSON", role="system")
    s(
        "To accrate the result, I need to know the tools you want to use.\n"
        f"The available tools are:\n"
        f"{tool_names}\n\n"
        f"The prompt: {message}\n\n"
        "If you need to use a tool to process the message, please find the tool names in the available tools."
        "If no tool is really needed, please respond with an empty list.\n"
        "Please respond in JSON format using the following format:\n"
        """{"tools": ["tool1", "tool2", ...]}"""
    )
    response = await s.invoke_async(ai, response_format={"type": "json_object"})
    try:
        response_json = json.loads(response.choices[0].message.content)
        tool_names = response_json.get("tools", [])
    except Exception:  # XXX
        return []
    return format_tools(tool_names)
