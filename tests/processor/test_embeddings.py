"""
Tests for the Azure OpenAI Embedding Service.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.processor.embeddings.azure_openai import (
    EmbeddingService,
    embed_texts,
    EMBEDDING_DIMENSIONS,
)


class TestEmbeddingService:
    """Tests for EmbeddingService class."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock Azure OpenAI client."""
        client = MagicMock()
        
        # Create mock response
        mock_response = MagicMock()
        mock_embedding_1 = MagicMock()
        mock_embedding_1.index = 0
        mock_embedding_1.embedding = [0.1] * EMBEDDING_DIMENSIONS
        
        mock_embedding_2 = MagicMock()
        mock_embedding_2.index = 1
        mock_embedding_2.embedding = [0.2] * EMBEDDING_DIMENSIONS
        
        mock_response.data = [mock_embedding_1, mock_embedding_2]
        client.embeddings.create.return_value = mock_response
        
        return client

    @patch("src.processor.embeddings.azure_openai.AzureOpenAI")
    def test_embed_texts(self, mock_azure_openai, mock_openai_client):
        """Test embedding multiple texts."""
        mock_azure_openai.return_value = mock_openai_client
        
        service = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            model="text-embedding-ada-002",
        )
        
        embeddings = service.embed_texts(["text 1", "text 2"])
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) == EMBEDDING_DIMENSIONS
        assert len(embeddings[1]) == EMBEDDING_DIMENSIONS
        mock_openai_client.embeddings.create.assert_called_once()

    @patch("src.processor.embeddings.azure_openai.AzureOpenAI")
    def test_embed_single_text(self, mock_azure_openai, mock_openai_client):
        """Test embedding a single text."""
        # Adjust mock for single text
        mock_response = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.index = 0
        mock_embedding.embedding = [0.1] * EMBEDDING_DIMENSIONS
        mock_response.data = [mock_embedding]
        mock_openai_client.embeddings.create.return_value = mock_response
        mock_azure_openai.return_value = mock_openai_client
        
        service = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            model="text-embedding-ada-002",
        )
        
        embedding = service.embed_text("single text")
        
        assert len(embedding) == EMBEDDING_DIMENSIONS

    @patch("src.processor.embeddings.azure_openai.AzureOpenAI")
    def test_embed_empty_list(self, mock_azure_openai):
        """Test embedding empty list returns empty list."""
        service = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            model="text-embedding-ada-002",
        )
        
        embeddings = service.embed_texts([])
        
        assert embeddings == []

    @patch("src.processor.embeddings.azure_openai.AzureOpenAI")
    def test_batch_processing(self, mock_azure_openai, mock_openai_client):
        """Test that large lists are processed in batches."""
        mock_azure_openai.return_value = mock_openai_client
        
        # Create response for each batch call
        def create_response(*args, **kwargs):
            texts = kwargs.get("input", [])
            response = MagicMock()
            response.data = [
                MagicMock(index=i, embedding=[0.1] * EMBEDDING_DIMENSIONS)
                for i in range(len(texts))
            ]
            return response
        
        mock_openai_client.embeddings.create.side_effect = create_response
        
        service = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            model="text-embedding-ada-002",
            batch_size=2,
        )
        
        # Embed 5 texts with batch size 2 = 3 API calls
        texts = [f"text {i}" for i in range(5)]
        embeddings = service.embed_texts(texts)
        
        assert len(embeddings) == 5
        assert mock_openai_client.embeddings.create.call_count == 3

    @patch("src.processor.embeddings.azure_openai.AzureOpenAI")
    @patch("src.processor.embeddings.azure_openai.time.sleep")
    def test_retry_on_rate_limit(self, mock_sleep, mock_azure_openai, mock_openai_client):
        """Test retry logic on rate limit errors."""
        from openai import RateLimitError
        
        mock_azure_openai.return_value = mock_openai_client
        
        # Fail twice, succeed on third try
        mock_response = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.index = 0
        mock_embedding.embedding = [0.1] * EMBEDDING_DIMENSIONS
        mock_response.data = [mock_embedding]
        
        mock_openai_client.embeddings.create.side_effect = [
            RateLimitError("Rate limit", response=MagicMock(), body=None),
            RateLimitError("Rate limit", response=MagicMock(), body=None),
            mock_response,
        ]
        
        service = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            model="text-embedding-ada-002",
        )
        
        embeddings = service.embed_texts(["test"])
        
        assert len(embeddings) == 1
        assert mock_sleep.call_count == 2

    @patch("src.processor.embeddings.azure_openai.AzureOpenAI")
    def test_handles_empty_text(self, mock_azure_openai, mock_openai_client):
        """Test that empty texts are handled gracefully."""
        mock_azure_openai.return_value = mock_openai_client
        
        service = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            model="text-embedding-ada-002",
        )
        
        # Should not raise, empty strings replaced with placeholder
        embeddings = service.embed_texts(["", "valid text"])
        
        assert len(embeddings) == 2


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @patch("src.processor.embeddings.azure_openai._get_service")
    def test_embed_texts_function(self, mock_get_service):
        """Test the module-level embed_texts function."""
        mock_service = MagicMock()
        mock_service.embed_texts.return_value = [[0.1] * EMBEDDING_DIMENSIONS]
        mock_get_service.return_value = mock_service
        
        result = embed_texts(["test"])
        
        assert len(result) == 1
        mock_service.embed_texts.assert_called_once_with(["test"])



