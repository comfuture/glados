import pytest
import os
import sys

# add to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from glados.util.langchain import (  # noqa: E402
    TextLoader,
    load_documents,
    split_documents,
    count_tokens,
)  # noqa


def test_load_markdown():
    loader = TextLoader("test/sample.md")
    documents = loader.load()
    assert len(documents) == 1
    docs = split_documents(documents)
    for doc in docs:
        assert count_tokens(doc.page_content) <= 2000
        print(doc.metadata)
        print(doc.page_content)


def test_load_documents():
    documents = load_documents("test/sample.md")
    assert len(documents) == 1
    docs = split_documents(documents)
    for doc in docs:
        assert count_tokens(doc.page_content) <= 2000
        print(doc.metadata)
        print(doc.page_content)


def test_load_document_with_split():
    docs1 = load_documents("test/sample.md")
    docs2 = load_documents("test/sample.md", split=True)
    assert len(docs1) == 1
    docs3 = split_documents(docs1)
    assert len(docs2) == len(docs3)


def test_load_pdf():
    doc = load_documents("test/sample.pdf")
    docs = split_documents(doc)
    for doc in docs:
        assert count_tokens(doc.page_content) <= 2000
        print(doc.metadata)
        print(doc.page_content)


def test_load_docx():
    doc = load_documents("test/sample.docx")
    assert len(doc) == 1
    docs = split_documents(doc)
    for doc in docs:
        assert count_tokens(doc.page_content) <= 2000
        print(doc.metadata)
        print(doc.page_content)
