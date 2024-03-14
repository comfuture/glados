import re
from typing import Generator
from .block import MrkDwn, MarkDown, SourceCode, Image, Context, Header


def format_response(text: str) -> Generator[dict, None, None]:
    """Format markdown text using slack block kit.
    Slack can use limited markdown syntax, so we need to convert it to block kit.
    """
    block_type = None  # markdown, quote, list, sourcecode
    buff = ""

    for line in text.split("\n"):
        if not line:
            buff += "\n"
            continue
        if block_type != "sourcecode" and line.startswith("# "):  # heading
            yield Header(line[2:])
            continue
        if line.startswith("```"):  # code block
            # flush recent block
            if block_type != "sourcecode":
                if buff.strip():
                    yield MarkDown(buff)
                    buff = ""
                lang = line[3:]
                if lang:
                    yield Context(f"Source: {lang}")
                block_type = "sourcecode"
                continue
            if block_type == "sourcecode":  # recent block type is source code,
                yield SourceCode(buff)
                buff = ""
                block_type = None
            continue
        if line.startswith("!["):
            if buff.strip():
                yield MarkDown(buff)
            image_match = re.match(r"!\[(.*)\]\((.*)\)", line)
            if image_match:
                yield Image(image_match.group(2), image_match.group(1))
            buff = ""
            continue
        buff += line + "\n"
    if buff.strip():
        if block_type == "sourcecode":
            yield SourceCode(buff)
        else:
            yield MarkDown(buff)
