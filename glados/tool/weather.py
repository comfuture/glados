from typing import Annotated, Optional
from enum import Enum

__all__ = ("get_weather",)


class TemperatureUnit(str, Enum):
    """The unit of the temperature."""

    celsius = "celsius"
    fahrenheit = "fahrenheit"


async def get_weather(
    city: Annotated[str, "The name of the city you want to get the weather of."],
    unit: Annotated[
        Optional[str], "The unit of the temperature.", TemperatureUnit
    ] = "celcius",
) -> Annotated[str, "The weather of the city."]:
    """Get the weather of the city."""
    return f"The weather of {city} is sunny. The temperature is 20 degrees {unit}."
