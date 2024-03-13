from typing import Optional
import re

__all__ = ["MrkDwn", "MarkDown", "SourceCode", "Context", "Image"]


def MrkDwn(text: str) -> dict:
    return {"type": "mrkdwn", "text": text}


def MarkDown(text: str) -> dict:
    """Format as markdown block."""
    heading = re.match(r"^(#+) (\s+)", text)
    listitem = re.match(r"^(\d+\. |\s*(-\*) )(\s+)", text)
    if heading:
        text = f"*{heading.group(2)}*"
    elif listitem:
        text = f"- {listitem.group(3)}"
    return {
        "type": "section",
        "text": MrkDwn(text),
    }


def SourceCode(text: str) -> dict:
    """Format as source code block."""
    return MarkDown(f"```\n{text}```")


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
