from typing import Annotated, Optional
from random import randint
from glados.tool import plugin


@plugin()
def roll_dice(
    sides: Annotated[Optional[int], "The number of sides of the dice."] = 6,
) -> Annotated[int, "The result of the dice roll."]:
    """Roll dice."""
    return randint(1, sides)
