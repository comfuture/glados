from datetime import datetime
from ipny.tool import plugin
from ipny.session import SessionManager


@plugin(name="System Date", icon="📅")
async def get_date() -> dict:
    """returns current date and time"""
    session = SessionManager.current
    context = session.context.get()
    return {
        "date": context.get(
            "current_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        ),
        "timezone": context.get("timezone", "UTC"),
    }
