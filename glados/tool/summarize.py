import os
import tempfile
from typing import Annotated, Optional
from textwrap import dedent
from openai import AsyncOpenAI
import httpx
import trafilatura
from glados.session import SessionManager
from glados.tool import plugin

openai = AsyncOpenAI()


async def get_text_content(file_id: str) -> str:
    """
    Retrieves the text content from a file.

    Args:
        file_id (str): The ID of the file to retrieve the content from.

    Returns:
        str: The text content of the file.

    Raises:
        ValueError: If the file format is not supported.
    """
    file_info = await openai.files.retrieve(file_id)
    filename, ext = os.path.splitext(file_info.filename)
    if ext not in (".pdf", ".txt", ".md"):
        raise ValueError("Unsupported file format.")

    raise NotImplementedError("This function is not implemented yet.")
    # parser = DocumentParser()
    parser = None

    file_content = await openai.files.retrieve_content(file_id)

    if ext in (".txt", ".md"):
        return file_content

    with tempfile.NamedTemporaryFile(suffix=ext) as f:
        f.write(file_content)
        f.flush()
        parsed_content = parser.parse(f.name)
        return "".join(node.text for node in parsed_content.nodes)


async def summarize(text: str, *, instructions: Optional[str] = None) -> str:
    """
    Summarizes the given text by generating bullet points for the main ideas, steps, and vocabulary.

    Args:
        text (str): The text to be summarized.
        prompt (Optional[str]): An optional prompt to provide additional instructions for the summary.

    Returns:
        str: The summarized text.
    """
    prompt = dedent("""\
        You are an expert with superb comprehension and communication skills, 
        skilled in reading, understanding, and summarizing the main points of 
        large sections of dense texts. Your task is to summarize the text, 
        providing bullet points for the main ideas, steps, and vocabulary.
        The summary result should be concise and informative.
        
        """)
    if instructions:
        prompt += dedent(f"""\
            During the summary, you should follow the instructions of the following instructions.
            Instructions: {instructions}""")

    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2000,
        messages=[
            {"role": "system", "content": "Summarize the text."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Text content:\n{text}"},
                    {"type": "text", "text": prompt},
                ],
            },
        ],
    )

    return response.content[0].text


async def summarize_recent_file(
    instructions: Annotated[
        Optional[str], "The prompt for the summarization."
    ] = "Please summarize the content of the file.",
):
    """Summarize the content of the most recent file in the current thread."""
    session = SessionManager.current
    thread_id = session.thread_id

    messages = await openai.beta.threads.messages.list(
        thread_id=thread_id, order="desc", limit=5
    )

    file_id = None
    for message in messages:
        if message.attachments:
            attachment = message.attachments[-1]
            file_id = attachment.file_id
            break

    if not file_id:
        return "No file found in the thread."

    try:
        text_content = await get_text_content(file_id)
    except ValueError:
        return "Unsupported file format."

    summary = await summarize(text_content, instructions=instructions)
    return {"summary": summary}


@plugin(name="Summarize", icon="🌍")
async def summarize_url(
    url: Annotated[str, "The URL to summarize."],
    instructions: Annotated[
        Optional[str], "The additional instructions for the summarization."
    ] = None,
):
    """summarize the content of the URL"""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        }
        r = httpx.get(url, headers=headers, follow_redirects=True)
        r.raise_for_status()
        text_content = trafilatura.extract(r.text)
        return await summarize(text_content, instructions=instructions)
    except Exception as e:
        return {"error": str(e)}
