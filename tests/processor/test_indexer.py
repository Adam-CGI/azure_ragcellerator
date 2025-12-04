"""
Tests for the Cognitive Search Indexer.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.processor.indexers.cognitive_search import (
    SearchIndexer,
    upsert_chunks,
    delete_by_source_path,
)
from src.processor.models import Chunk


class TestSearchIndexer:
    """Tests for SearchIndexer class."""

    @pytest.fixture
    def mock_search_client(self):
        """Create a mock SearchClient."""
        client = MagicMock()
        
        # Mock upload response
        mock_result = MagicMock()
        mock_result.succeeded = True
        mock_result.key = "doc-1"
        mock_result.error_message = None
        client.upload_documents.return_value = [mock_result]
        
        return client

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            Chunk(
                chunk_id=0,
                content="First chunk content",
                source_path="/documents/test.pdf",
                file_name="test.pdf",
                total_chunks=2,
            ),
            Chunk(
                chunk_id=1,
                content="Second chunk content",
                source_path="/documents/test.pdf",
                file_name="test.pdf",
                total_chunks=2,
            ),
        ]

    @pytest.fixture
    def sample_embeddings(self):
        """Create sample embeddings for testing."""
        return [
            [0.1] * 1536,
            [0.2] * 1536,
        ]

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_upsert_chunks(
        self, mock_client_class, mock_search_client, sample_chunks, sample_embeddings
    ):
        """Test upserting chunks with embeddings."""
        mock_client_class.return_value = mock_search_client
        
        # Mock successful upload
        mock_results = [MagicMock(succeeded=True) for _ in sample_chunks]
        mock_search_client.upload_documents.return_value = mock_results
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        success, failed = indexer.upsert_chunks(sample_chunks, sample_embeddings)
        
        assert success == 2
        assert failed == 0
        mock_search_client.upload_documents.assert_called_once()

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_upsert_chunks_without_embeddings(
        self, mock_client_class, mock_search_client, sample_chunks
    ):
        """Test upserting chunks without pre-computed embeddings."""
        mock_client_class.return_value = mock_search_client
        
        mock_results = [MagicMock(succeeded=True) for _ in sample_chunks]
        mock_search_client.upload_documents.return_value = mock_results
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        success, failed = indexer.upsert_chunks(sample_chunks)
        
        assert success == 2
        assert failed == 0

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_upsert_empty_chunks(self, mock_client_class, mock_search_client):
        """Test upserting empty chunk list."""
        mock_client_class.return_value = mock_search_client
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        success, failed = indexer.upsert_chunks([])
        
        assert success == 0
        assert failed == 0
        mock_search_client.upload_documents.assert_not_called()

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_upsert_mismatched_embeddings(
        self, mock_client_class, mock_search_client, sample_chunks
    ):
        """Test that mismatched embeddings raise error."""
        mock_client_class.return_value = mock_search_client
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        # Only one embedding for two chunks
        with pytest.raises(ValueError, match="must match"):
            indexer.upsert_chunks(sample_chunks, [[0.1] * 1536])

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_upsert_partial_failure(
        self, mock_client_class, mock_search_client, sample_chunks
    ):
        """Test handling partial upload failures."""
        mock_client_class.return_value = mock_search_client
        
        # First succeeds, second fails
        mock_results = [
            MagicMock(succeeded=True, key="chunk-0"),
            MagicMock(succeeded=False, key="chunk-1", error_message="Index error"),
        ]
        mock_search_client.upload_documents.return_value = mock_results
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        success, failed = indexer.upsert_chunks(sample_chunks)
        
        assert success == 1
        assert failed == 1

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_delete_by_source_path(self, mock_client_class, mock_search_client):
        """Test deleting documents by source path."""
        mock_client_class.return_value = mock_search_client
        
        # Mock search results
        mock_search_results = [
            {"id": "doc1"},
            {"id": "doc2"},
        ]
        mock_search_client.search.return_value = iter(mock_search_results)
        
        # Mock delete results
        mock_delete_results = [
            MagicMock(succeeded=True),
            MagicMock(succeeded=True),
        ]
        mock_search_client.delete_documents.return_value = mock_delete_results
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        deleted = indexer.delete_by_source_path("/documents/test.pdf")
        
        assert deleted == 2
        mock_search_client.delete_documents.assert_called_once()

    @patch("src.processor.indexers.cognitive_search.SearchClient")
    def test_delete_nonexistent_source(self, mock_client_class, mock_search_client):
        """Test deleting from nonexistent source path."""
        mock_client_class.return_value = mock_search_client
        mock_search_client.search.return_value = iter([])
        
        indexer = SearchIndexer(
            endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index",
        )
        
        deleted = indexer.delete_by_source_path("/documents/nonexistent.pdf")
        
        assert deleted == 0
        mock_search_client.delete_documents.assert_not_called()


class TestChunkToSearchDocument:
    """Tests for Chunk to search document conversion."""

    def test_to_search_document_basic(self):
        """Test basic chunk to document conversion."""
        chunk = Chunk(
            chunk_id=0,
            content="Test content",
            source_path="/documents/test.pdf",
            file_name="test.pdf",
        )
        
        doc = chunk.to_search_document()
        
        assert doc["id"] == chunk.document_id
        assert doc["content"] == "Test content"
        assert doc["sourcePath"] == "/documents/test.pdf"
        assert doc["fileName"] == "test.pdf"
        assert doc["chunkId"] == 0
        assert "contentVector" not in doc  # No embedding

    def test_to_search_document_with_embedding(self):
        """Test chunk conversion with embedding."""
        embedding = [0.1] * 1536
        chunk = Chunk(
            chunk_id=0,
            content="Test content",
            source_path="/documents/test.pdf",
            file_name="test.pdf",
            embedding=embedding,
        )
        
        doc = chunk.to_search_document()
        
        assert doc["contentVector"] == embedding

    def test_to_search_document_with_page_number(self):
        """Test chunk conversion with page number."""
        chunk = Chunk(
            chunk_id=0,
            content="Test content",
            source_path="/documents/test.pdf",
            file_name="test.pdf",
            page_number=5,
            total_chunks=10,
        )
        
        doc = chunk.to_search_document()
        
        assert doc["pageNumber"] == 5
        assert doc["totalChunks"] == 10


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @patch("src.processor.indexers.cognitive_search._get_indexer")
    def test_upsert_chunks_function(self, mock_get_indexer):
        """Test the module-level upsert_chunks function."""
        mock_indexer = MagicMock()
        mock_indexer.upsert_chunks.return_value = (5, 0)
        mock_get_indexer.return_value = mock_indexer
        
        chunks = [MagicMock() for _ in range(5)]
        success, failed = upsert_chunks(chunks)
        
        assert success == 5
        assert failed == 0
        mock_indexer.upsert_chunks.assert_called_once()

    @patch("src.processor.indexers.cognitive_search._get_indexer")
    def test_delete_by_source_path_function(self, mock_get_indexer):
        """Test the module-level delete_by_source_path function."""
        mock_indexer = MagicMock()
        mock_indexer.delete_by_source_path.return_value = 3
        mock_get_indexer.return_value = mock_indexer
        
        deleted = delete_by_source_path("/test/path.pdf")
        
        assert deleted == 3
        mock_indexer.delete_by_source_path.assert_called_once_with("/test/path.pdf")



