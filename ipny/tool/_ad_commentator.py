import os
import subprocess
import tempfile
import contextlib
import requests
from typing import Optional
from openai import AsyncOpenAI
from ipny.tool import plugin
from ipny.session import Session, SessionManager
import base64


@contextlib.contextmanager
def get_thumbnails(video_url: str, interval=1):
    """
    Generate thumbnails from a video at a specified interval.

    Args:
        video_url (str): The URL or path of the video file.
        interval (int, optional): The interval between thumbnails in seconds. Defaults to 1.

    Yields:
        str: The path to the directory containing the generated thumbnails.
    """
    with tempfile.TemporaryDirectory() as output_dir:
        command = [
            "ffmpeg",
            "-i",
            video_url,
            "-vf",
            f"fps=1/{interval},scale=-1:512",  # Added scale filter to resize the height to 512
            "-q:v",
            "2",  # Change this value to change the quality of the thumbnails
            f"{output_dir}/thumbnail_%03d.jpg",
        ]

        # Run the command
        subprocess.run(command, check=True)

        yield output_dir


async def get_transcript(video_url: str):
    """
    Generate transcript from a video.

    Args:
        video_url (str): The URL or path of the video file.

    Returns:
        str: The transcript of the video.
    """
    openai = AsyncOpenAI()

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_file_path = os.path.join(temp_dir, "audio.wav")

        # Define the command to extract audio from video
        command = [
            "ffmpeg",
            "-i",
            video_url,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            audio_file_path,
        ]
        print(" ".join(command))

        subprocess.run(command, check=True)

        with open(audio_file_path, "rb") as f:
            tr = await openai.audio.transcriptions.create(
                file=f,
                model="whisper-1",
            )
            print(f"{tr.text=}")
    return tr.text


# @plugin(name="AD Commentator", icon="🗣️")
async def commentate_ad(
    video_url: str,
    *,
    prompt: Optional[str] = "Please commentate and analyze this ad video",
) -> dict:
    """commentates and analyzes an ad video"""

    # download slack file
    SessionManager.current
    session = SessionManager.current
    context = session.context.get()
    slack = context.get("platform_client")

    # special handling for slack files
    if video_url.startswith("https://files.slack.com"):
        ext = video_url.split(".")[-1]
        r = requests.get(video_url, headers={"Authorization": f"Bearer {slack.token}"})
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
            temp_file.write(r.content)
            video_url = temp_file.name

    # extract transcript from video
    transcript = await get_transcript(video_url)

    # create thumbnails from video
    with get_thumbnails(video_url, interval=5) as d:
        # List all jpg files in directory 'd'
        thumbnail_files = [
            os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jpg")
        ]

        # Make list of base64 encoded images
        encoded_images = []
        for file in thumbnail_files:
            with open(file, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
                encoded_images.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_string}"
                        },
                    }
                )

    s = Session(
        model="gpt-4-vision-preview",
        system_prompt=(
            "You are a marketing expert. Commentate and analyze this ad video."
        ),
    )
    text = (
        "Please refer to the still images of the ad video and the transcript of the ad "
        "and provide a detailed analysis of the ad video."
        f"\n\nTranscript: \n{transcript}\n\n"
        "Please provide your opinion on the ad video in artistic perspective and marketing perspective with the following prompt:"
        f"\n\nPrompt: {prompt}\n\n"
        "In marketing perspective, Provide focused advice on whether these standards are met:\n"
        "- Does the advertisement align with the marketing strategy?\n"
        "- Is it targeting the correct consumer?\n"
        "- Is it speaking from the consumer's perspective?\n"
        "- Is it focusing on the most important elements?\n"
        "- What action is it requesting?\n"
        "Please commentate and analyze this ad video in this template:\n"
        "(Main story line of the ad)\n(Artistic perspective)\n(Marketing perspective)\n(The final rating of the ad)\n"
        "each section should be at least 4-10 sentences long."
        "Please respond in the language of the ad video transcript."
    )
    print(f"{text=} {len(encoded_images)=}")
    content = [
        {"type": "text", "text": text},
        *encoded_images,
    ]
    s(content)
    result = await s.invoke_async(AsyncOpenAI())
    return {
        "result": result.choices[0].message.content,
    }
