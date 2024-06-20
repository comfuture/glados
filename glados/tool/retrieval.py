import os
from typing import Annotated, Optional, Generator
from bson import ObjectId
from datetime import datetime, timezone
from openai import AsyncOpenAI
from openparse import processing, DocumentParser, Node
from glados.backend.db import use_db
from glados.tool import plugin
from glados.session import SessionManager


def split_documents(filepath: str | os.PathLike) -> Generator[Node, None, None]:
    """
    Splits a document into smaller segments using a semantic ingestion pipeline.

    Args:
        filepath (str | os.PathLike): The path to the document file.

    Yields:
        Node: Each segment of the document.

    """
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    semantic_pipeline = processing.SemanticIngestionPipeline(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-3-small",
        min_tokens=512,
        max_tokens=2048,
    )
    parser = DocumentParser(
        # processing_pipeline=semantic_pipeline,
    )

    parsed_content = parser.parse(filepath)
    for node in parsed_content.nodes:
        yield node


async def save_document(
    file: Annotated[str | os.PathLike, "The path to the file to save."],
    *,
    namespace: Annotated[
        Optional[str], "The namespace to save the file in."
    ] = "default",
    user: Annotated[Optional[str], "The user who saved the file."] = None,
) -> Annotated[str, "The id of the saved document."]:
    """Keep a file for later retrieval"""
    now = datetime.now(timezone.utc)
    db = use_db()

    filename = os.path.basename(file)

    r = await db.get_collection("files").insert_one(
        {
            "namespace": namespace,
            "filename": filename,
            "user": user,
            "created_at": now,
            "updated_at": now,
        }
    )

    file_id = r.inserted_id

    openai = AsyncOpenAI()

    for node in split_documents(file):
        print(f"{node.text=}")
        if not node.text:
            continue
        response = await openai.embeddings.create(
            input=node.text,
            model="text-embedding-3-small",
            # user=user,
        )
        await db.get_collection("file_contents").insert_one(
            {
                "file_id": file_id,
                "namespace": namespace,
                "content": node.text,
                "embeddings": response.data[0].embedding,
                "created_at": now,
            }
        )

    return str(file_id)


async def list_documents(
    namespace: Annotated[str, "The namespace to list files from."] = "default",
    cursor: Annotated[Optional[str], "The cursor to continue listing from."] = None,
    limit: Annotated[Optional[int], "The maximum number of results to return."] = 10,
) -> Annotated[list[str], "The list of file keys."]:
    """List files."""
    db = use_db()
    cursor = db.collection("files").aggreaate(
        [
            {"$sort": {"created_at": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "key": 1}},
        ]
    )
    return [doc.get("_id") async for doc in cursor]


async def delete_document(
    file_id: Annotated[str, "The key of the file to delete."],
) -> Annotated[bool, "Whether the file was deleted."]:
    """Delete a file."""
    db = use_db()
    _id = ObjectId(file_id)
    await db.collection("file_contents").delete_many({"_id": _id})
    await db.collection("files").delete_one({"_id": _id})
    return True


async def search_document(
    query: Annotated[str, "The query to search for."],
    *,
    namespaces: Annotated[list[str], "The list of namespaces to search in."] = [
        "default"
    ],
    file_ids: Annotated[
        Optional[list[str]], "The list of file keys to search in."
    ] = None,
    limit: Annotated[Optional[int], "The maximum number of results to return."] = 3,
) -> Annotated[list[str], "The list of file contents that match the query."]:
    """Search the content of files."""
    openai = AsyncOpenAI()
    embeddings = await openai.embeddings.create(
        input=query, model="text-embedding-ada-002"
    )

    db = use_db()

    pre_filters = []
    if namespaces:
        pre_filters.append({"namespace": {"$in": namespaces}})
    if file_ids:
        pre_filters.append(
            {"_id": {"$in": [ObjectId(file_id) for file_id in file_ids]}}
        )

    cursor = db.get_collection("file_contents").aggregate(
        [
            {
                "$vectorSearch": {
                    "queryVector": embeddings.data[0].embedding,
                    "path": "embeddings",
                    "numCandidates": 100,
                    "index": "vector_index",
                    "limit": 20,
                }
            },
            {
                "$project": {
                    "namespace": 1,
                    "content": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
            # {"$match": {"$and": pre_filters}},
            {"$limit": limit},
        ]
    )
    return [doc async for doc in cursor]


# @plugin(name="Retrieval", icon="🔍")
async def retrieval(query: Annotated[str, "The query to search for."]) -> dict:
    """Retrieve data for accurate search."""
    session = SessionManager.current
    context = session.context.get()

    namespaces = [
        f"channel/{context.get('channel')}",
        f"session/{session.session_id}",
        f"user/{context.get('user')}",
    ]

    guide = (
        "Write a comprehensive answer to the question by using provided search result in the best way you can. "
        "If you can't find enough information in the search results and you're not sure about the answer,"
        "Just answer 'I'm not sure about the answer'. "
        "Please respond in the language of the question even the search results are written in another language."
    )
    results = [
        {"content": doc.get("content"), "score": doc.get("score")}
        async for doc in search_document(query, namespaces=namespaces)
    ]
    return {
        "results": results,
        "guide": guide,
    }
