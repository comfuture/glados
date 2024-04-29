import mimetypes

from typing import Iterable, Optional
from openai import AsyncOpenAI
from openai.types.beta.threads.message_create_params import Attachment
from openai._types import FileTypes, NotGiven, NOT_GIVEN  # XXX: interal import

RUNNABLE_FILE_TYPES = [
    "text/x-c",
    "text/x-csharp",
    "text/x-c++",
    # "application/msword", # XXX: Commented out to avoid running DOC files
    # "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # XXX: Commented out to avoid running DOCX files
    "text/html",
    "text/x-java",
    "application/json",
    "text/markdown",
    # "application/pdf", # XXX: Commented out to avoid running PDF files
    "text/x-php",
    # "application/vnd.openxmlformats-officedocument.presentationml.presentation", # XXX: Commented out to avoid running PPTX files
    "text/x-python",
    "text/x-script.python",
    "text/x-ruby",
    "text/x-tex",
    "text/plain",
    "text/css",
    "text/javascript",
    "application/x-sh",
    "application/typescript",
    "application/csv",
    "image/jpeg",
    "image/gif",
    "image/png",
    "application/x-tar",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/xml",
    "application/zip",
]

SEARCHABLE_FILE_TYPES = [
    "text/x-c",
    "text/x-csharp",
    "text/x-c++",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
    "text/x-java",
    "application/json",
    "text/markdown",
    "application/pdf",
    "text/x-php",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/x-python",
    "text/x-script.python",
    "text/x-ruby",
    "text/x-tex",
    "text/plain",
    "text/css",
    "text/javascript",
    "application/x-sh",
    "application/typescript",
]


async def upload_files(
    files: Optional[Iterable[FileTypes]] = None,
) -> list[Attachment] | None:
    """
    Uploads a list of files and returns a list of attachments.

    Args:
        files (Iterable[FileTypes]): A list of files to be uploaded.

    Returns:
        list[Attachment]: A list of attachments containing the uploaded file IDs and tools.

    """
    if not files:
        return NOT_GIVEN

    openai = AsyncOpenAI()
    attachments = []
    for file_ in files:
        uploaded = await openai.files.create(
            file=file_,
            purpose="assistants",
        )

        if len(file_) == 3:
            # If the content type is provided, use it
            content_type = file_[2]
        else:
            # Guess the content type from the file extension
            content_type = mimetypes.guess_type(file_[0])[0]

        tools = []
        if content_type in RUNNABLE_FILE_TYPES:
            tools.append({"type": "code_interpreter"})
        if content_type in SEARCHABLE_FILE_TYPES:
            tools.append({"type": "file_search"})

        attachments.append(
            {
                "file_id": uploaded.id,
                "tools": tools,
            }
        )
    return attachments
