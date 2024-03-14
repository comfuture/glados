from datetime import datetime
from glados.tool import plugin


@plugin(name="System Date", icon="📅")
async def get_date() -> str:
    """returns current date"""
    return datetime.now().isoformat()
