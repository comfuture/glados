import pytest
from glados.backend.db import use_db


@pytest.mark.asyncio
async def test_db_connection():
    """test db connection"""
    db = use_db()
    assert db is not None
    assert db.name == "glados"
    assert db.client is not None
    assert db.client.server_info() is not None
