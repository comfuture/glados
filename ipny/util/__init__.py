import os
import uuid
from io import BytesIO
import tiktoken
import requests
import boto3


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text."""
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    return len(tokens)


def is_image_url(url: str) -> bool:
    """Check if a URL is an image."""
    r = requests.head(url, allow_redirects=True)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        return False
    headers = {k.lower(): v for k, v in r.headers.items()}
    return headers.get("content-type", "").startswith("image/")


def make_public_url(image: BytesIO, ext: str = "jpg") -> str:
    """Upload an image to image server and return a public URL."""
    filename = f"{str(uuid.uuid4())}.{ext}"
    savedir = os.path.join("ipny", filename[:2])
    r = requests.post(
        f"https://i.sori.io/data/{savedir}/",
        auth=("admin", "1111"),
        files={
            "file": (filename, image),
        },
    )
    data = r.json()
    image_url = data.get("urls")[0].get("url").replace("http", "https")
    print(f"{image_url=}")
    return {"url": image_url}
