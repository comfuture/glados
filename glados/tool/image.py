from typing import Annotated, Optional, TypedDict
from enum import Enum
from io import BytesIO
from base64 import b64decode
from openai import AsyncOpenAI
from glados.util import make_public_url
from glados.session import Session
from glados.tool import plugin

__all__ = (
    "process_image",
    "draw_image",
)


# @plugin(name="Vision", icon="👁️")
async def process_image(
    image_url: Annotated[str, "The public URL of the image."],
    prompt: Annotated[
        Optional[str], "The prompt for the image. Please use the language of user"
    ] = "Please describe the image details",
) -> dict:
    """Let AI to process an image with a prompt using Vision API."""
    print(f"process_image {image_url=} {prompt=}")
    client = AsyncOpenAI()
    s = Session(
        model="gpt-4-turbo",
        system_prompt=(
            "You are a programming interface for vision model."
            "You can describe, query with the image, grab information from the image, etc."
        ),
    )
    content = [
        {
            "type": "text",
            "text": (
                "Please describe the image in detail of the image and get answer with given prompt.\n"
                f"Prompt: {prompt}\n"
                "Use this template to respond:\n"
                """result: (The result of the image with prompt)\nannotation: (The detailed annotation of the image)"""
            ),
        },
        {"type": "image_url", "image_url": image_url},
    ]
    s(content)
    ret = await s.invoke_async(client)
    try:
        return ret.choices[0].message.content
    except Exception as e:
        return {"error": str(e)}


@plugin(name="dall-e-3", icon="🎨")
async def draw_image(
    prompt: Annotated[
        str,
        (
            "The prompt for the image.\n"
            "As a professional photographer, illustrator, and animator,"
            "You should use rich and descriptive language when describing your prompts."
            "The prompt should be in English. The prompt should be starts with "
            "'A photo of', 'A 3D render of', 'An illustration of', or 'A painting of'. "
            "Including 5-10 descriptive keywords, camera & lens type, color tone and mood, time of day, style of photograph, and type of film "
            "joining with commas. While describing the prompt, you should refer to the recent chat history."
        ),
    ],
    style: Annotated[
        Optional[str], Enum("ImageStyle", "vivid natural"), "The style of the image."
    ] = "natural",
) -> TypedDict("ImageResult", {"url": str}):
    """Draw an image with a prompt."""
    client = AsyncOpenAI()
    ret = await client.images.generate(
        model="dall-e-3", prompt=prompt, style=style, response_format="b64_json"
    )
    b64string = ret.data[0].b64_json
    image = b64decode(b64string)
    image_url = make_public_url(BytesIO(image), ext="webp")
    return {"url": image_url}
