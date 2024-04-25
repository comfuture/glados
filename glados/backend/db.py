import os
import urllib.parse
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)

_connections = {}


def use_db() -> AsyncIOMotorDatabase:
    """Get the database to use."""
    dsn = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    parsed = urllib.parse.urlparse(dsn)
    dbname = os.environ.get("MONGODB_DB", parsed.path[1:])
    if dsn not in _connections:
        client = AsyncIOMotorClient(dsn)
        _connections[dsn] = client[dbname]
    return _connections[dsn]


def use_connection(name: str) -> AsyncIOMotorCollection:
    """Get the collection to use."""
    return use_db().get_collection(name)
