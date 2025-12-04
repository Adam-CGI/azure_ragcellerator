"""
Azure RAGcelerator - Blob Storage Service

Handles downloading documents and metadata from Azure Blob Storage.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

from azure.storage.blob import BlobClient, BlobServiceClient

from ..config import get_settings
from ..models import Document

logger = logging.getLogger(__name__)


class BlobService:
    """Service for interacting with Azure Blob Storage."""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the blob service.
        
        Args:
            connection_string: Azure Storage connection string.
                              Defaults to settings.
        """
        self.connection_string = connection_string or get_settings().storage_connection_string
        self._client: Optional[BlobServiceClient] = None

    @property
    def client(self) -> BlobServiceClient:
        """Get or create the BlobServiceClient."""
        if self._client is None:
            self._client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        return self._client

    def download_blob(self, blob_url: str) -> bytes:
        """
        Download blob content from a URL.
        
        Args:
            blob_url: Full URL to the blob or blob path.
        
        Returns:
            bytes: The blob content.
        
        Raises:
            ValueError: If the URL is invalid.
            Exception: If download fails.
        """
        logger.info(f"Downloading blob from: {blob_url}")
        
        blob_client = self._get_blob_client(blob_url)
        
        try:
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            logger.info(f"Downloaded {len(content)} bytes from {blob_url}")
            return content
        except Exception as e:
            logger.error(f"Failed to download blob {blob_url}: {e}")
            raise

    def get_blob_metadata(self, blob_url: str) -> dict:
        """
        Get blob metadata and properties.
        
        Args:
            blob_url: Full URL to the blob or blob path.
        
        Returns:
            dict: Blob metadata including name, size, content_type, etc.
        """
        logger.debug(f"Getting metadata for: {blob_url}")
        
        blob_client = self._get_blob_client(blob_url)
        
        try:
            properties = blob_client.get_blob_properties()
            
            metadata = {
                "name": properties.name,
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "created_on": properties.creation_time,
                "last_modified": properties.last_modified,
                "etag": properties.etag,
            }
            
            # Include custom metadata if present
            if properties.metadata:
                metadata["custom"] = properties.metadata
            
            return metadata
        except Exception as e:
            logger.error(f"Failed to get metadata for {blob_url}: {e}")
            raise

    def download_document(self, blob_url: str) -> Document:
        """
        Download a document with its metadata.
        
        Args:
            blob_url: Full URL to the blob.
        
        Returns:
            Document: The downloaded document with metadata.
        """
        metadata = self.get_blob_metadata(blob_url)
        content = self.download_blob(blob_url)
        
        return Document(
            source_path=blob_url,
            file_name=metadata["name"].split("/")[-1],
            content=content,
            content_type=metadata.get("content_type", "application/octet-stream"),
            metadata=metadata,
            uploaded_at=metadata.get("created_on"),
        )

    def _get_blob_client(self, blob_url: str) -> BlobClient:
        """
        Get a BlobClient from a URL or path.
        
        Args:
            blob_url: Full URL or container/blob path.
        
        Returns:
            BlobClient: Client for the blob.
        """
        # Check if it's a full URL
        if blob_url.startswith("https://"):
            return BlobClient.from_blob_url(
                blob_url=blob_url,
                credential=self.connection_string,
            )
        
        # Parse as container/blob path
        parts = blob_url.strip("/").split("/", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid blob path: {blob_url}. "
                "Expected format: container/blob_name or full URL"
            )
        
        container_name, blob_name = parts
        container_client = self.client.get_container_client(container_name)
        return container_client.get_blob_client(blob_name)

    def list_blobs(
        self,
        container_name: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> list[str]:
        """
        List blobs in a container.
        
        Args:
            container_name: Container to list. Defaults to documents container.
            prefix: Optional prefix to filter blobs.
        
        Returns:
            list[str]: List of blob names.
        """
        container_name = container_name or get_settings().documents_container_name
        container_client = self.client.get_container_client(container_name)
        
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]


# Module-level convenience functions
_service: Optional[BlobService] = None


def _get_service() -> BlobService:
    """Get or create the global blob service instance."""
    global _service
    if _service is None:
        _service = BlobService()
    return _service


def download_blob(blob_url: str) -> bytes:
    """
    Download blob content from a URL.
    
    Args:
        blob_url: Full URL to the blob.
    
    Returns:
        bytes: The blob content.
    """
    return _get_service().download_blob(blob_url)


def get_blob_metadata(blob_url: str) -> dict:
    """
    Get blob metadata.
    
    Args:
        blob_url: Full URL to the blob.
    
    Returns:
        dict: Blob metadata.
    """
    return _get_service().get_blob_metadata(blob_url)



