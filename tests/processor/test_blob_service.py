"""
Tests for the Blob Storage Service.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.processor.storage.blob_service import BlobService


class TestBlobService:
    """Tests for BlobService class."""

    @pytest.fixture
    def mock_blob_client(self):
        """Create a mock BlobClient."""
        client = MagicMock()
        
        # Mock download
        download_stream = MagicMock()
        download_stream.readall.return_value = b"test content"
        client.download_blob.return_value = download_stream
        
        # Mock properties
        properties = MagicMock()
        properties.name = "documents/test.pdf"
        properties.size = 1024
        properties.content_settings.content_type = "application/pdf"
        properties.creation_time = datetime(2024, 1, 1)
        properties.last_modified = datetime(2024, 1, 2)
        properties.etag = "test-etag"
        properties.metadata = {"uploaded_by": "test-user"}
        client.get_blob_properties.return_value = properties
        
        return client

    @pytest.fixture
    def mock_container_client(self, mock_blob_client):
        """Create a mock ContainerClient."""
        client = MagicMock()
        client.get_blob_client.return_value = mock_blob_client
        return client

    @pytest.fixture
    def mock_service_client(self, mock_container_client):
        """Create a mock BlobServiceClient."""
        client = MagicMock()
        client.get_container_client.return_value = mock_container_client
        return client

    @patch("src.processor.storage.blob_service.BlobServiceClient")
    def test_download_blob_from_path(
        self, mock_client_class, mock_service_client, mock_blob_client
    ):
        """Test downloading blob using container/blob path."""
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        service = BlobService(connection_string="test-connection-string")
        content = service.download_blob("documents/test.pdf")
        
        assert content == b"test content"
        mock_blob_client.download_blob.assert_called_once()

    @patch("src.processor.storage.blob_service.BlobClient")
    def test_download_blob_from_url(self, mock_blob_client_class, mock_blob_client):
        """Test downloading blob using full URL."""
        mock_blob_client_class.from_blob_url.return_value = mock_blob_client
        
        service = BlobService(connection_string="test-connection-string")
        content = service.download_blob(
            "https://teststorage.blob.core.windows.net/documents/test.pdf"
        )
        
        assert content == b"test content"
        mock_blob_client_class.from_blob_url.assert_called_once()

    @patch("src.processor.storage.blob_service.BlobServiceClient")
    def test_get_blob_metadata(
        self, mock_client_class, mock_service_client, mock_blob_client
    ):
        """Test retrieving blob metadata."""
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        service = BlobService(connection_string="test-connection-string")
        metadata = service.get_blob_metadata("documents/test.pdf")
        
        assert metadata["name"] == "documents/test.pdf"
        assert metadata["size"] == 1024
        assert metadata["content_type"] == "application/pdf"
        assert metadata["custom"]["uploaded_by"] == "test-user"

    @patch("src.processor.storage.blob_service.BlobServiceClient")
    def test_download_document(
        self, mock_client_class, mock_service_client
    ):
        """Test downloading a complete document with metadata."""
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        service = BlobService(connection_string="test-connection-string")
        document = service.download_document("documents/test.pdf")
        
        assert document.file_name == "test.pdf"
        assert document.content == b"test content"
        assert document.content_type == "application/pdf"
        assert document.source_path == "documents/test.pdf"

    def test_invalid_blob_path(self):
        """Test that invalid blob paths raise ValueError."""
        service = BlobService(connection_string="test-connection-string")
        
        with pytest.raises(ValueError, match="Invalid blob path"):
            service._get_blob_client("invalid-path-without-container")

    @patch("src.processor.storage.blob_service.BlobServiceClient")
    def test_list_blobs(self, mock_client_class, mock_service_client):
        """Test listing blobs in a container."""
        mock_client_class.from_connection_string.return_value = mock_service_client
        
        # Mock blob list
        mock_blobs = [MagicMock(name="doc1.pdf"), MagicMock(name="doc2.pdf")]
        mock_service_client.get_container_client.return_value.list_blobs.return_value = mock_blobs
        
        service = BlobService(connection_string="test-connection-string")
        blobs = service.list_blobs("documents")
        
        assert len(blobs) == 2


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @patch("src.processor.storage.blob_service._get_service")
    def test_download_blob_function(self, mock_get_service):
        """Test the module-level download_blob function."""
        from src.processor.storage.blob_service import download_blob
        
        mock_service = MagicMock()
        mock_service.download_blob.return_value = b"content"
        mock_get_service.return_value = mock_service
        
        result = download_blob("test/blob.pdf")
        
        assert result == b"content"
        mock_service.download_blob.assert_called_once_with("test/blob.pdf")

    @patch("src.processor.storage.blob_service._get_service")
    def test_get_blob_metadata_function(self, mock_get_service):
        """Test the module-level get_blob_metadata function."""
        from src.processor.storage.blob_service import get_blob_metadata
        
        mock_service = MagicMock()
        mock_service.get_blob_metadata.return_value = {"name": "test.pdf"}
        mock_get_service.return_value = mock_service
        
        result = get_blob_metadata("test/blob.pdf")
        
        assert result["name"] == "test.pdf"



