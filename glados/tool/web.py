from typing import Annotated, Optional
from glados.tool import plugin


# @plugin(name="Web Search", icon="🔍")
async def search_web(
    query: Annotated[str, "The query to search."],
    limit: Annotated[Optional[int], "The number of results to return."] = 3,
) -> list:
    """Search the web with the given query."""
    return [
        {
            "title": "Search Result 1",
            "url": "https://example.com",
            "description": "This is the first search result.",
        }
    ]


# @plugin(name="Get web content", icon="📄")
async def get_web_content(
    url: Annotated[str, "The URL of the web page."],
) -> str:
    """Get the content of the web page."""
    return "This is the content of the web page."
