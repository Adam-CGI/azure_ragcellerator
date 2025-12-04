"""
Tests for the Search Service.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.ui.search_service import SearchService, SearchResult, search


class TestSearchService:
    """Tests for SearchService class."""

    @pytest.fixture
    def mock_search_client(self):
        """Create a mock SearchClient."""
        client = MagicMock()
        
        # Mock search results
        mock_results = [
            {
                "id": "doc1#chunk_0",
                "content": "This is the first result content.",
                "fileName": "document1.pdf",
                "sourcePath": "/documents/document1.pdf",
                "chunkId": 0,
                "@search.score": 0.95,
                "@search.highlights": {"content": ["first result"]},
            },
            {
                "id": "doc2#chunk_0",
                "content": "This is the second result content.",
                "fileName": "document2.pdf",
                "sourcePath": "/documents/document2.pdf",
                "chunkId": 0,
                "@search.score": 0.85,
            },
        ]
        client.search.return_value = iter(mock_results)
        
        return client

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock Azure OpenAI client."""
        client = MagicMock()
        
        # Mock embedding response
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        client.embeddings.create.return_value = mock_response
        
        return client

    @patch("src.ui.search_service.SearchClient")
    @patch("src.ui.search_service.AzureOpenAI")
    def test_search_hybrid(
        self, mock_openai_class, mock_search_class, mock_search_client, mock_openai_client
    ):
        """Test hybrid search with vector and keyword."""
        mock_search_class.return_value = mock_search_client
        mock_openai_class.return_value = mock_openai_client
        
        service = SearchService(
            search_endpoint="https://test.search.windows.net",
            search_api_key="test-key",
            index_name="test-index",
            openai_endpoint="https://test.openai.azure.com",
            openai_api_key="openai-key",
            embedding_model="text-embedding-ada-002",
        )
        
        results = service.search("test query", top_k=10)
        
        assert len(results) == 2
        assert results[0].file_name == "document1.pdf"
        assert results[0].score == 0.95
        mock_openai_client.embeddings.create.assert_called_once()

    @patch("src.ui.search_service.SearchClient")
    @patch("src.ui.search_service.AzureOpenAI")
    def test_search_keyword_only(
        self, mock_openai_class, mock_search_class, mock_search_client, mock_openai_client
    ):
        """Test keyword-only search without vector."""
        mock_search_class.return_value = mock_search_client
        mock_openai_class.return_value = mock_openai_client
        
        service = SearchService(
            search_endpoint="https://test.search.windows.net",
            search_api_key="test-key",
            index_name="test-index",
            openai_endpoint="https://test.openai.azure.com",
            openai_api_key="openai-key",
        )
        
        results = service.search("test query", use_vector=False)
        
        assert len(results) == 2
        mock_openai_client.embeddings.create.assert_not_called()

    @patch("src.ui.search_service.SearchClient")
    @patch("src.ui.search_service.AzureOpenAI")
    def test_search_empty_query(self, mock_openai_class, mock_search_class):
        """Test that empty query returns empty results."""
        service = SearchService(
            search_endpoint="https://test.search.windows.net",
            search_api_key="test-key",
            index_name="test-index",
            openai_endpoint="https://test.openai.azure.com",
            openai_api_key="openai-key",
        )
        
        results = service.search("")
        
        assert results == []

    @patch("src.ui.search_service.SearchClient")
    @patch("src.ui.search_service.AzureOpenAI")
    def test_search_with_semantic_ranking(
        self, mock_openai_class, mock_search_class, mock_search_client, mock_openai_client
    ):
        """Test search with semantic ranking."""
        # Add reranker score to results
        mock_results = [
            {
                "id": "doc1#chunk_0",
                "content": "First result",
                "fileName": "doc1.pdf",
                "sourcePath": "/docs/doc1.pdf",
                "chunkId": 0,
                "@search.score": 0.80,
                "@search.reranker_score": 0.95,
            },
        ]
        mock_search_client.search.return_value = iter(mock_results)
        mock_search_class.return_value = mock_search_client
        mock_openai_class.return_value = mock_openai_client
        
        service = SearchService(
            search_endpoint="https://test.search.windows.net",
            search_api_key="test-key",
            index_name="test-index",
            openai_endpoint="https://test.openai.azure.com",
            openai_api_key="openai-key",
        )
        
        results = service.search("test query", use_semantic=True)
        
        assert len(results) == 1
        # Should use reranker score instead of raw score
        assert results[0].score == 0.95


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_from_document(self):
        """Test creating SearchResult from document dict."""
        doc = {
            "content": "Test content",
            "fileName": "test.pdf",
            "sourcePath": "/test/test.pdf",
            "chunkId": 5,
            "@search.highlights": {"content": ["highlighted text"]},
        }
        
        result = SearchResult.from_document(doc, score=0.85)
        
        assert result.content == "Test content"
        assert result.file_name == "test.pdf"
        assert result.source_path == "/test/test.pdf"
        assert result.chunk_id == 5
        assert result.score == 0.85
        assert result.highlights == ["highlighted text"]

    def test_from_document_missing_fields(self):
        """Test creating SearchResult with missing optional fields."""
        doc = {
            "content": "Test content",
        }
        
        result = SearchResult.from_document(doc, score=0.5)
        
        assert result.content == "Test content"
        assert result.file_name == ""
        assert result.source_path == ""
        assert result.chunk_id == 0
        assert result.highlights is None


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @patch("src.ui.search_service._get_service")
    def test_search_function(self, mock_get_service):
        """Test the module-level search function."""
        mock_service = MagicMock()
        mock_service.search.return_value = [
            SearchResult(
                content="Result",
                file_name="doc.pdf",
                source_path="/doc.pdf",
                score=0.9,
            )
        ]
        mock_get_service.return_value = mock_service
        
        results = search("test query", top_k=5)
        
        assert len(results) == 1
        mock_service.search.assert_called_once_with("test query", 5)



