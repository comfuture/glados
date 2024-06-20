from typing import IO
import json
import tiktoken
import os

from langchain.chat_models import ChatOpenAI

from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.document_loaders.powerpoint import UnstructuredPowerPointLoader
from langchain.document_loaders.excel import UnstructuredExcelLoader
from langchain.document_loaders.html import UnstructuredHTMLLoader
from langchain.document_loaders.url import UnstructuredURLLoader
from langchain.chains.llm import LLMChain
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)

from trafilatura import extract as extract_html, fetch_url


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text."""
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    return len(tokens)


def load_documents(file_path: os.PathLike | str, split=False) -> list[Document]:
    """Load documents from a file path."""
    path = os.fspath(file_path)
    _, ext = os.path.splitext(path)
    if ext == ".pdf":
        loader = PyPDFLoader(file_path=path)
        docs = loader.load()
    elif ext == ".docx":
        loader = Docx2txtLoader(file_path=path)
        docs = loader.load()
    elif ext == ".pptx":
        loader = UnstructuredPowerPointLoader(file_path=path)
        docs = loader.load()
    elif ext == ".xlsx":
        loader = UnstructuredExcelLoader(file_path=path)
        docs = loader.load()
    elif ext == ".html":
        loader = UnstructuredHTMLLoader(file_path=path)
        docs = loader.load()
    else:
        loader = TextLoader(file_path=path)
        docs = loader.load()
    if split:
        docs = split_documents(docs)
    return docs


# def load_url(url: str, max_tokens: int = 2000):
#     loader = UnstructuredURLLoader(urls=[url])
#     documents = loader.load()
#     return documents
#     llm = LLMOpenAI(temperature=1)
#     # TODO: if document tokens < max_tokens return documents
#     chain = load_summarize_chain(llm, chain_type="map_reduce", verbose=True)
#     documents = chain.run(documents)
#     return documents


# def split_documents(documents: list[Document], max_tokens: int = 2000):
#     splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)
#     splitted = splitter.split_documents(documents=documents)
#     return splitted


def split_text(
    text: str,
    chunk_size=2000,
    chunk_overlap=100,
    headers_to_split_on=[("#", "Header 1"), ("##", "Header 2")],
) -> list[Document]:
    """Split a text into a list of documents."""
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_docs = splitter.split_text(text)

    token_splitter = TokenTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return token_splitter.split_documents(md_docs)


def split_documents(
    docs=list[Document],
    chunk_size=2000,
    chunk_overlap=100,
    headers_to_split_on=[("#", "Header 1"), ("##", "Header 2")],
) -> list[Document]:
    """Split a list of documents into a list of documents."""
    doc_texts = "\n".join([doc.page_content for doc in docs])
    splitted = split_text(doc_texts, chunk_size, chunk_overlap, headers_to_split_on)
    return splitted


def summaries_documents(documents: list[Document], max_tokens: int = 2000):
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-1106", temperature=0)
    map_prompt = PromptTemplate.from_template(
        "Please identify the main theme of the original set of documents.\n"
        "The set of documents:\n {docs}\n"
        "You MUST use the language of the original set of documents."
    )
    map_chain = LLMChain(llm=llm, prompt=map_prompt)
    reduce_prompt = PromptTemplate.from_template(
        "The following is set of summaries: \n{docs}\n"
        "Take these and distill it into a final, "
        "consolidated summary of the main themes in the set of summaries."
        "You MUST use the language of the original set of summaries."
    )
    reduce_chain = LLMChain(llm=llm, prompt=reduce_prompt)
    combine_documents_chain = StuffDocumentsChain(
        llm_chain=reduce_chain, document_variable_name="docs"
    )
    reduce_documents_chain = ReduceDocumentsChain(
        # This is final chain that is called.
        combine_documents_chain=combine_documents_chain,
        # If documents exceed context for `StuffDocumentsChain`
        collapse_documents_chain=combine_documents_chain,
        # The maximum number of tokens to group documents into.
        token_max=max_tokens,
    )

    map_reduce_chain = MapReduceDocumentsChain(
        # Map chain
        llm_chain=map_chain,
        # Reduce chain
        reduce_documents_chain=reduce_documents_chain,
        # The variable name in the llm_chain to put the documents in
        document_variable_name="docs",
        # Return the results of the map steps in the output
        return_intermediate_steps=False,
    )
    return map_reduce_chain.run(documents)


def load_url(url: str, max_tokens: int = 2000):
    response = fetch_url(url, decode=True)
    data = extract_html(response, url=url, output_format="json")
    data = json.loads(data)
    num_tokens = count_tokens(data.get("text", ""))
    doc = Document(
        page_content=data.get("text", ""),
        metadata={
            "title": data.get("title", ""),
            "excerpt": data.get("excerpt", ""),
            "url": url,
        },
    )

    if num_tokens < max_tokens:
        return [doc]
    # TODO: if document tokens < max_tokens return documents
    print("Token exceeded, summarizing...")
    docs = split_documents([doc], max_tokens=max_tokens)
    documents = summaries_documents(docs)
    return documents
