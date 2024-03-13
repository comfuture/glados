import os
import re
import tempfile
from typing import Annotated, Optional, IO, AnyStr
import shortuuid
from datetime import datetime, timezone
from openai import OpenAI
from ..backend.db import use_db


async def save_file(
    *,
    file: Annotated[Optional[IO[AnyStr]], "The file to save."],
    file_path: Annotated[Optional[str], "The name of the file to save."] = None,
    namespace: Annotated[
        Optional[str], "The namespace to save the file in."
    ] = "default",
    user: Annotated[Optional[str], "The user who saved the file."] = None,
) -> Annotated[str, "The key of the saved file."]:
    """Save a file."""
    if not file and not file_path:
        raise ValueError("Either file or file_path must be provided.")

    if file and file_path:
        raise ValueError("Only one of file or file_path can be provided.")

    if not file_path and file:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            if file.name:
                f.name = file.name
            f.write(file.read())
            file_path = f.name

    filename = os.path.basename(file.name or f"{shortuuid.uuid()}.txt")

    openai = OpenAI()

    now = datetime.now(timezone.utc)

    db = use_db()

    r = await db.get_collection("files").insert_one(
        {
            "name": filename,
            "namespace": namespace,
            "user": user,
            "created_at": now,
        }
    )

    file_id = r.inserted_id

    load_documents(file_path, split=True)

    for section in file.read().split("\n\n"):  # XXX
        embeddings = openai.embeddings.create(
            input=section,
            model="text-embedding-ada-002",
            user=user,
        )
        await db.get_collection("file_contents").insert_one(
            {
                "file_id": file_id,
                "namespace": namespace,
                "content": section,
                "embeddings": embeddings.data,
                "created_at": now,
            }
        )

    return uri  # "glados:///default/file.txt"


async def list_files(
    path: Annotated[str, "The path to list files from."] = "/",
    *,
    namespace: Annotated[str, "The namespace to list files from."] = "default",
    cursor: Annotated[Optional[str], "The cursor to continue listing from."] = None,
    limit: Annotated[Optional[int], "The maximum number of results to return."] = 10,
) -> Annotated[list[str], "The list of file keys."]:
    """List files."""
    db = use_db()
    cursor = db.collection("files").aggreaate(
        [
            {
                "$match": {
                    "path": {"$regex": rf"^glados:///{namespace}{re.escape(path)}"},
                }
            },
            {"$sort": {"created_at": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "key": 1}},
        ]
    )
    return [doc.get("key") async for doc in cursor]
    return ["glados:///default/file1.txt", "glados:///default/file2.txt"]


async def delete_file(
    key: Annotated[str, "The key of the file to delete."],
) -> Annotated[bool, "Whether the file was deleted."]:
    """Delete a file."""
    db = use_db()
    await db.collection("file_contents").delete_many({"key": key})
    await db.collection("files").delete_one({"key": key})
    return True


async def search_file_content(
    query: Annotated[str, "The query to search for."],
    *,
    namespace: Annotated[str, "The namespace to search in."] = "default",
    path: Annotated[str, "The path to search from."] = "/",
    limit: Annotated[Optional[int], "The maximum number of results to return."] = 3,
) -> Annotated[list[str], "The list of file contents that match the query."]:
    """Search the content of files."""
    openai = OpenAI()
    embeddings = openai.embeddings.create(input=query, model="text-embedding-ada-002")

    db = use_db()
    cursor = db.get_collection("file_contents").aggregate(
        [
            {
                "$vectorSearch": {
                    "queryVector": embeddings.data,
                    "path": "embeddings",
                    "numCandidates": 100,
                    "index": "vector_index",
                    "limit": 20,
                }
            },
            {
                "$match": {
                    "namespace": namespace,
                    "path": {"$regex": f"^{re.escape(path)}"},
                }
            },
            {"$limit": limit},
        ]
    )
    return [doc.get("content") async for doc in cursor]
