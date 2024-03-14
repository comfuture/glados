from typing import Annotated, Optional
from enum import Enum
from io import BytesIO
from base64 import b64decode
from openai import OpenAI
from glados.util import make_public_url
from glados.session import Session
from glados.tool import plugin

__all__ = (
    "process_image",
    "draw_image",
)


@plugin(name="Vision", icon="👁️")
async def process_image(
    image_url: Annotated[str, "The public URL of the image."],
    prompt: Annotated[
        Optional[str], "The prompt for the image"
    ] = "Please describe the image details",
) -> dict:
    """Let AI to process an image with a prompt using Vision API."""
    client = OpenAI()
    s = Session(
        model="gpt-4-vision-preview",
        system_prompt=(
            "You are a programming interface for vision model."
            "You can describe, query with the image, grab information from the image, etc.",
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
    ret = s.invoke(client, max_tokens=2000)
    try:
        return ret.choices[0].message.content
    except Exception as e:
        return {"error": str(e)}


@plugin(name="Dall-e", icon="🎨")
async def draw_image(
    prompt: Annotated[
        str,
        (
            "The prompt for the image.\n"
            "As a professional photographer, illustrator, and animator,"
            "You should use rich and descriptive language when describing your prompts."
            "The prompt should be in English. The prompt should be starts with 'A photo of', 'A 3D render of', 'An illustration of', or 'A painting of'."
            "Including 5-10 descriptive keywords, camera & lens type, color tone and mood, time of day, style of photograph, and type of film."
        ),
    ],
    style: Annotated[
        Optional[str], Enum("ImageStyle", "vivid natural"), "The style of the image."
    ] = "natural",
    # enhance_prompt: Annotated[bool, "Whether to enhance the prompt."] = True,
) -> dict:
    """Draw an image with a prompt."""
    client = OpenAI()
    if False:  # XXX
        s = Session(
            model="gpt-3.5-turbo",
            system_prompt=(
                "As a professional photographer, illustrator, and animator, "
                "You should use rich and descriptive language when describing your prompts. "
                "DESCRIBE in English."
            ),
        )
        formulars = {
            "photo": "(image we're prompting), (5 descriptive keywords), (camera type), (camera lens type), (time of day), (style of photograph), (type of film)",
            "3D": "(render style) 3D render of (image we're prompting), (5 descriptive keywords), 4k, high resolution, trending in artstation",
            "illustration": "Illustration of (image we're prompting), (5 descriptive keywords), (style of illustration), (color tone and mood), captivating, artstation 3",
            "painting": "(painting method and style) painting of (image we're prompting), (5 descriptive keywords), (color tone and mood), inspired (reference style)",
        }
        formular = formulars[kind or "photo"]
        s(
            "Please make an image prompt for me with your professional knowledge and imagination.\n"
            "Please respond only with the image prompt without any other information.\n"
            f"Please use the following templates to describe the image:\n{formular}\n\n"
            f"The image I want:\n{prompt}\n"
        )
        print(f"{s[...]=}")
        r = s.invoke(client)
        prompt = r.choices[0].message.content

    print(f"tool::draw_image {prompt=}, {style=}")

    ret = client.images.generate(
        model="dall-e-3", prompt=prompt, style=style, response_format="b64_json"
    )
    b64string = ret.data[0].b64_json
    image = b64decode(b64string)
    image_url = make_public_url(BytesIO(image), ext="webp")
    return {"url": image_url}
