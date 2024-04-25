import pytest
from glados.tool.retrieval import search_document


@pytest.mark.asyncio
async def test_search_document():
    """Test search_document."""
    result = await search_document("실시간 맛집 예약 서비스 관리자")
    print(result)
    assert result == "This is the content of the document."
