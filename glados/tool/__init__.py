import os
import glob
import importlib.util
import inspect
import json
from typing import Optional
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from function_schema import get_function_schema
from ..assistant import OpenAI
from ..session import Session


def plugin(fn, meta: Optional[dict] = {}):
    async def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(fn):
            ret = await fn(**kwargs)
        else:
            ret = fn(**kwargs)
        return ret

    wrapper.__glados_plugin__ = True
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__annotations__ = fn.__annotations__
    # wrapper.__defaults__ = getattr(fn, "__defaults__", None)
    # wrapper.__kwdefaults__ = getattr(fn, "__kwdefaults__", None)
    wrapper.__meta__ = meta
    return wrapper


# Load all tools
all_tools = {}
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

    # Get all functions in the module
    functions = inspect.getmembers(module, inspect.isfunction)

    # Add the functions to the all_tools dictionary
    for function_name, function in functions:
        all_tools[function_name] = {
            "schema": get_function_schema(function),
            "function": function,
        }
print(f"Loaded tools {all_tools=}")


async def noop(**kwargs):
    """Do nothing."""
    pass


async def invoke_function(function_name: str, **kwargs):
    """Invoke a tool function.

    even if the function is not found, it should not raise an error, but return a message that the function is not found.
    if the function is corountine, it automatically awaits it.
    """
    tool = all_tools.get(function_name, {"function": noop})
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
    return [
        {"type": "function", "function": all_tools.get(tool_name)["schema"]}
        for tool_name in tool_names
    ]


async def choose_tools(message: str) -> list[dict] | None:
    """automatically choose tools from a message."""
    ai = OpenAI()
    tool_names = "\n".join(
        [
            f"- {tool_name}: {impl['schema'].get('description', tool_name)}"
            for tool_name, impl in all_tools.items()
        ]
    )

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
    response = s.invoke(ai, response_format={"type": "json_object"})
    try:
        response_json = json.loads(response.choices[0].message.content)
        tool_names = response_json.get("tools", [])
    except Exception:  # XXX
        return []
    return format_tools(tool_names)
