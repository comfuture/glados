import random
import pytest
from unittest.mock import patch
from openai import OpenAI
from openai.types import CreateEmbeddingResponse


openai = OpenAI()


def mock_create_embedding(*args, **kwargs) -> CreateEmbeddingResponse:
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="not implemented")
@patch.object(openai.embeddings, "create", new=mock_create_embedding)
async def test_create_embedding():
    """test create embedding"""
    text = "Hello, world!"
    embeddings = openai.embeddings.create(input=text)
    assert embeddings is not None
