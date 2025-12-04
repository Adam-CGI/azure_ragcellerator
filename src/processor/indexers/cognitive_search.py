"""
Azure RAGcelerator - Cognitive Search Indexer

Handles upserting and deleting documents in Azure Cognitive Search.
"""

import logging
from datetime import datetime
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import IndexingResult

from ..config import get_settings
from ..models import Chunk

logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 1000  # Maximum documents per batch upload


class SearchIndexer:
    """Service for indexing documents in Azure Cognitive Search."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
    ):
        """
        Initialize the search indexer.
        
        Args:
            endpoint: Azure Cognitive Search endpoint URL.
            api_key: Azure Cognitive Search admin API key.
            index_name: Name of the search index.
        """
        settings = get_settings()
        
        self.endpoint = endpoint or settings.search_endpoint
        self.api_key = api_key or settings.search_api_key
        self.index_name = index_name or settings.search_index_name

        self._client: Optional[SearchClient] = None

    @property
    def client(self) -> SearchClient:
        """Get or create the SearchClient."""
        if self._client is None:
            credential = AzureKeyCredential(self.api_key)
            self._client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=credential,
            )
        return self._client

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: Optional[list[list[float]]] = None,
    ) -> tuple[int, int]:
        """
        Upsert chunks to the search index.
        
        Args:
            chunks: List of chunks to upsert.
            embeddings: Optional list of embeddings corresponding to chunks.
                       If provided, must be same length as chunks.
        
        Returns:
            tuple[int, int]: (successful_count, failed_count)
        """
        if not chunks:
            logger.warning("No chunks to upsert")
            return 0, 0

        if embeddings and len(embeddings) != len(chunks):
            raise ValueError(
                f"Embeddings count ({len(embeddings)}) must match "
                f"chunks count ({len(chunks)})"
            )

        # Assign embeddings to chunks if provided
        if embeddings:
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding

        # Convert chunks to search documents
        processed_at = datetime.utcnow()
        documents = [chunk.to_search_document(processed_at) for chunk in chunks]

        logger.info(f"Upserting {len(documents)} documents to index '{self.index_name}'")

        # Process in batches
        total_success = 0
        total_failed = 0

        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            success, failed = self._upsert_batch(batch)
            total_success += success
            total_failed += failed

        logger.info(
            f"Upsert complete: {total_success} succeeded, {total_failed} failed"
        )

        return total_success, total_failed

    def _upsert_batch(self, documents: list[dict]) -> tuple[int, int]:
        """
        Upsert a batch of documents.
        
        Args:
            documents: List of documents to upsert.
        
        Returns:
            tuple[int, int]: (successful_count, failed_count)
        """
        try:
            results = self.client.upload_documents(documents)
            
            success = sum(1 for r in results if r.succeeded)
            failed = len(results) - success

            # Log failed documents
            for result in results:
                if not result.succeeded:
                    logger.error(
                        f"Failed to index document {result.key}: "
                        f"{result.error_message}"
                    )

            return success, failed

        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            return 0, len(documents)

    def delete_by_source_path(self, source_path: str) -> int:
        """
        Delete all chunks from a source document.
        
        This enables re-processing by removing old chunks before
        adding updated ones.
        
        Args:
            source_path: Source path to delete chunks for.
        
        Returns:
            int: Number of documents deleted.
        """
        logger.info(f"Deleting documents for source path: {source_path}")

        try:
            # Search for all documents with this source path
            results = self.client.search(
                search_text="*",
                filter=f"sourcePath eq '{source_path}'",
                select=["id"],
                top=10000,  # Maximum allowed
            )

            # Collect document IDs
            doc_ids = [{"id": doc["id"]} for doc in results]

            if not doc_ids:
                logger.info(f"No documents found for source path: {source_path}")
                return 0

            # Delete in batches
            total_deleted = 0
            for i in range(0, len(doc_ids), BATCH_SIZE):
                batch = doc_ids[i:i + BATCH_SIZE]
                delete_results = self.client.delete_documents(batch)
                deleted = sum(1 for r in delete_results if r.succeeded)
                total_deleted += deleted

            logger.info(f"Deleted {total_deleted} documents for {source_path}")
            return total_deleted

        except Exception as e:
            logger.error(f"Failed to delete documents for {source_path}: {e}")
            raise

    def get_document_count(self) -> int:
        """
        Get the total number of documents in the index.
        
        Returns:
            int: Document count.
        """
        try:
            results = self.client.search(
                search_text="*",
                include_total_count=True,
                top=0,
            )
            return results.get_count() or 0
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    def get_source_paths(self) -> list[str]:
        """
        Get unique source paths in the index.
        
        Returns:
            list[str]: List of unique source paths.
        """
        try:
            results = self.client.search(
                search_text="*",
                select=["sourcePath"],
                facets=["sourcePath"],
                top=0,
            )
            
            facets = results.get_facets()
            if facets and "sourcePath" in facets:
                return [f["value"] for f in facets["sourcePath"]]
            return []
        except Exception as e:
            logger.error(f"Failed to get source paths: {e}")
            return []


# Module-level convenience functions
_indexer: Optional[SearchIndexer] = None


def _get_indexer() -> SearchIndexer:
    """Get or create the global indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = SearchIndexer()
    return _indexer


def upsert_chunks(
    chunks: list[Chunk],
    embeddings: Optional[list[list[float]]] = None,
) -> tuple[int, int]:
    """
    Upsert chunks to the search index.
    
    Args:
        chunks: List of chunks to upsert.
        embeddings: Optional list of embeddings.
    
    Returns:
        tuple[int, int]: (successful_count, failed_count)
    """
    return _get_indexer().upsert_chunks(chunks, embeddings)


def delete_by_source_path(source_path: str) -> int:
    """
    Delete all chunks from a source document.
    
    Args:
        source_path: Source path to delete.
    
    Returns:
        int: Number of documents deleted.
    """
    return _get_indexer().delete_by_source_path(source_path)



