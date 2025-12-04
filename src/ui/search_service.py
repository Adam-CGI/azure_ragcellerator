"""
Azure RAGcelerator - Search Service

Hybrid search (keyword + vector) integration with Azure Cognitive Search.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    
    content: str
    file_name: str
    source_path: str
    score: float
    chunk_id: int = 0
    highlights: Optional[list[str]] = None

    @classmethod
    def from_document(cls, doc: dict, score: float) -> "SearchResult":
        """Create SearchResult from a search document."""
        return cls(
            content=doc.get("content", ""),
            file_name=doc.get("fileName", ""),
            source_path=doc.get("sourcePath", ""),
            score=score,
            chunk_id=doc.get("chunkId", 0),
            highlights=doc.get("@search.highlights", {}).get("content"),
        )


class SearchService:
    """Service for hybrid search on Azure Cognitive Search."""

    def __init__(
        self,
        search_endpoint: Optional[str] = None,
        search_api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        openai_endpoint: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_api_version: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize the search service.
        
        Args:
            search_endpoint: Cognitive Search endpoint.
            search_api_key: Cognitive Search API key.
            index_name: Search index name.
            openai_endpoint: Azure OpenAI endpoint.
            openai_api_key: Azure OpenAI API key.
            openai_api_version: OpenAI API version.
            embedding_model: Embedding model deployment name.
        """
        settings = get_settings()
        
        self.search_endpoint = search_endpoint or settings.search_endpoint
        self.search_api_key = search_api_key or settings.search_api_key
        self.index_name = index_name or settings.search_index_name
        self.openai_endpoint = openai_endpoint or settings.openai_endpoint
        self.openai_api_key = openai_api_key or settings.openai_api_key
        self.openai_api_version = openai_api_version or settings.openai_api_version
        self.embedding_model = embedding_model or settings.embedding_model

        self._search_client: Optional[SearchClient] = None
        self._openai_client: Optional[AzureOpenAI] = None

    @property
    def search_client(self) -> SearchClient:
        """Get or create the SearchClient."""
        if self._search_client is None:
            credential = AzureKeyCredential(self.search_api_key)
            self._search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.index_name,
                credential=credential,
            )
        return self._search_client

    @property
    def openai_client(self) -> AzureOpenAI:
        """Get or create the Azure OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.openai_endpoint,
                api_key=self.openai_api_key,
                api_version=self.openai_api_version,
            )
        return self._openai_client

    def search(
        self,
        query: str,
        top_k: int = 10,
        use_vector: bool = True,
        use_semantic: bool = True,
    ) -> list[SearchResult]:
        """
        Perform hybrid search (keyword + vector).
        
        Args:
            query: Search query text.
            top_k: Maximum number of results to return.
            use_vector: Whether to include vector search.
            use_semantic: Whether to use semantic ranking.
        
        Returns:
            list[SearchResult]: Search results sorted by relevance.
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        logger.info(f"Searching for: {query[:50]}...")

        try:
            # Build search parameters
            search_kwargs = {
                "search_text": query,
                "select": ["id", "content", "fileName", "sourcePath", "chunkId"],
                "top": top_k,
                "highlight_fields": "content",
            }

            # Add vector query if enabled
            if use_vector:
                query_embedding = self._get_embedding(query)
                vector_query = VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=top_k,
                    fields="contentVector",
                )
                search_kwargs["vector_queries"] = [vector_query]

            # Add semantic configuration if enabled
            if use_semantic:
                search_kwargs["query_type"] = "semantic"
                search_kwargs["semantic_configuration_name"] = "rag-semantic-config"

            # Execute search
            results = self.search_client.search(**search_kwargs)

            # Parse results
            search_results = []
            for result in results:
                score = result.get("@search.score", 0.0)
                if use_semantic:
                    # Use reranker score if available
                    score = result.get("@search.reranker_score", score)
                
                search_result = SearchResult.from_document(result, score)
                search_results.append(search_result)

            logger.info(f"Found {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def _get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for query text.
        
        Args:
            text: Text to embed.
        
        Returns:
            list[float]: Embedding vector.
        """
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=[text],
        )
        return response.data[0].embedding


# Module-level convenience functions
_service: Optional[SearchService] = None


def _get_service() -> SearchService:
    """Get or create the global search service."""
    global _service
    if _service is None:
        _service = SearchService()
    return _service


def search(query: str, top_k: int = 10) -> list[SearchResult]:
    """
    Perform hybrid search.
    
    Args:
        query: Search query text.
        top_k: Maximum results to return.
    
    Returns:
        list[SearchResult]: Search results.
    """
    return _get_service().search(query, top_k)



