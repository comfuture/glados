from typing import Annotated, Optional
from random import randint
from glados.tool import plugin
from glados.session import SessionManager


@plugin(name="Who Am I", icon="👤")
def whoami():
    """Get the user's info."""
    session = SessionManager.current
    info = session.context.get()
    return info
