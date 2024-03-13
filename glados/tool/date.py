from datetime import datetime

__all__ = ("get_date",)


async def get_date() -> str:
    """returns current date"""
    return datetime.now().isoformat()
