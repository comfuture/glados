from typing import Optional
import re

__all__ = ["MrkDwn", "MarkDown", "SourceCode", "Context", "Image"]


def MrkDwn(text: str) -> dict:
    text = re.sub(r"(\#+) (.*)", r"*\2*", text)
    text = re.sub(r"(\s*)\* (.*)\n", r"\1- \2\n", text)
    # text = re.sub(r"(https://[^\s^\)]+)", r"[\1](\1)", text)
    text = re.sub(r"\[(.*)\]\((.*)\)", r"<\2|\1>", text)

    return {"type": "mrkdwn", "text": text}


def MarkDown(text: str) -> dict:
    """Format as markdown block."""
    # TODO: format using new rich_text block
    return {
        "type": "section",
        "text": MrkDwn(text),
    }


def Header(text: str) -> dict:
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text, "emoji": True},
    }


def SourceCode(text: str) -> dict:
    """Format as source code block."""
    return {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_preformatted",
                "elements": [{"type": "text", "text": text}],
            },
        ],
    }


def Context(text: str) -> dict:
    """Format as context block."""
    return {
        "type": "context",
        "elements": [MrkDwn(text)],
    }


def Image(url: str, alt_text: Optional[str] = "image") -> dict:
    """Format as image block."""
    return {
        "type": "image",
        "image_url": url,
        "alt_text": alt_text,
    }


def AutoBlocks(markdown_text: str) -> list[dict]:
    """Automatically format text as blocks."""
    blocks = []
    for line in markdown_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append(MarkDown(line))
        elif line.startswith("```"):
            blocks.append(SourceCode(line))
        elif line.startswith("!["):
            image_match = re.match(r"!\[(.*)\]\((.*)\)", line)
            if image_match:
                alt_text = image_match.group(1)
                image_url = image_match.group(2)
            blocks.append(Image(image_url, alt_text=alt_text))
        else:
            blocks.append(MrkDwn(line))
    return blocks
