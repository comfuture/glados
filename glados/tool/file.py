from typing import Annotated, Optional, IO
from os import PathLike
from glados.tool import plugin
from openai import OpenAI


# async def upload_file(file: Annotated[IO | PathLike, "The file to upload."]) -> str:
#     """Upload a file. returns the file id."""
#     client = OpenAI()
#     r = client.files.create(file=file, purpose="assistant")
#     return r.id
#     ...


# @plugin(name="Read File", icon="📄")
# async def read_file(
#     file_id: Annotated[str, "The file id."],
#     query: Annotated[Optional[str], "The query to search in the file."] = None,
# ) -> str:
#     """Read the content of the file."""
#     return "This is the content of the file."
