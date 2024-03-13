import os
import uuid
from io import BytesIO
import requests
import boto3


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
    """Upload an image to Cloudflare R2 and return a public URL."""
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    access_key_id = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID")
    secret_access_key = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")
    public_r2_bucket_url = os.environ.get("PUBLIC_R2_BUCKET_URL")
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name="apac",
    )

    filename = f"tmp/{str(uuid.uuid4())}.{ext}"
    s3.upload_fileobj(image, "glados", filename, ExtraArgs={"ACL": "public-read"})
    file_url = f"{public_r2_bucket_url}/{filename}"
    return file_url
