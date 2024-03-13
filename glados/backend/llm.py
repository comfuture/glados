import tiktoken
from openai import OpenAI
from langchain.document_loaders.base.documents import Document
from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


def num_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text."""
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    return len(tokens)


def split_documents(
    docs=list[Document],
    chunk_size=2000,
    chunk_overlap=100,
    headers_to_split_on=[("#", "Header 1"), ("##", "Header 2")],
) -> list[Document]:
    """Split a list of documents into a list of documents."""

    # first, split the documents into chunks with markdown headers
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    md_docs = splitter.split_text(docs)

    # then, split the chunks into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return text_splitter.split_text(md_docs)
