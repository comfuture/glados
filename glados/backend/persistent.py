from ..backend.db import use_db
from ..session import Session


async def persist(key: str, data: dict):
    """Persist data."""
    pass


async def retrieve(key: str) -> dict:
    """Retrieve data."""
    return {}


async def save_thread(session: Session):
    """Save thread"""
    ...


async def load_thread(session_id: str):
    """Load thread"""
    return None
