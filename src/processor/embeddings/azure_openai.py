"""
Azure RAGcelerator - Azure OpenAI Embedding Service

Generates vector embeddings using Azure OpenAI.
"""

import logging
import time
from typing import Optional

from openai import AzureOpenAI, APIError, RateLimitError, APIConnectionError

from ..config import get_settings

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_DIMENSIONS = 1536  # text-embedding-ada-002 dimensions
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 60.0  # seconds


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
    ):
        """
        Initialize the embedding service.
        
        Args:
            endpoint: Azure OpenAI endpoint URL.
            api_key: Azure OpenAI API key.
            api_version: API version to use.
            model: Model deployment name.
            batch_size: Number of texts per API call.
        """
        settings = get_settings()
        
        self.endpoint = endpoint or settings.openai_endpoint
        self.api_key = api_key or settings.openai_api_key
        self.api_version = api_version or settings.openai_api_version
        self.model = model or settings.embedding_model
        self.batch_size = batch_size or settings.embedding_batch_size

        self._client: Optional[AzureOpenAI] = None

    @property
    def client(self) -> AzureOpenAI:
        """Get or create the Azure OpenAI client."""
        if self._client is None:
            self._client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
        return self._client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed.
        
        Returns:
            list[list[float]]: List of embedding vectors (1536 dimensions each).
        
        Raises:
            Exception: If embedding generation fails after retries.
        """
        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
            
            logger.debug(
                f"Processed batch {i // self.batch_size + 1}/"
                f"{(len(texts) + self.batch_size - 1) // self.batch_size}"
            )

        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed.
        
        Returns:
            list[float]: Embedding vector (1536 dimensions).
        """
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []

    def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts with retry logic.
        
        Args:
            texts: Batch of texts to embed.
        
        Returns:
            list[list[float]]: Embedding vectors.
        """
        delay = INITIAL_RETRY_DELAY
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                return self._embed_batch(texts)
            
            except RateLimitError as e:
                last_error = e
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}), "
                    f"waiting {delay:.1f}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, MAX_RETRY_DELAY)
            
            except APIConnectionError as e:
                last_error = e
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{MAX_RETRIES}), "
                    f"waiting {delay:.1f}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, MAX_RETRY_DELAY)
            
            except APIError as e:
                last_error = e
                if e.status_code and 500 <= e.status_code < 600:
                    logger.warning(
                        f"Server error (attempt {attempt + 1}/{MAX_RETRIES}), "
                        f"waiting {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, MAX_RETRY_DELAY)
                else:
                    # Non-retryable error
                    raise

        # All retries exhausted
        logger.error(f"Failed to generate embeddings after {MAX_RETRIES} attempts")
        raise last_error

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a single batch.
        
        Args:
            texts: Batch of texts to embed.
        
        Returns:
            list[list[float]]: Embedding vectors.
        """
        # Sanitize inputs - remove empty strings and truncate if needed
        clean_texts = []
        for text in texts:
            if text and text.strip():
                # Azure OpenAI has token limits; truncate very long texts
                # (8191 tokens for ada-002, roughly 4 chars per token)
                max_chars = 30000
                clean_texts.append(text[:max_chars] if len(text) > max_chars else text)
            else:
                # Use placeholder for empty text
                clean_texts.append(" ")

        response = self.client.embeddings.create(
            model=self.model,
            input=clean_texts,
        )

        # Extract embeddings in order
        embeddings = [None] * len(clean_texts)
        for item in response.data:
            embeddings[item.index] = item.embedding

        return embeddings


# Module-level convenience functions
_service: Optional[EmbeddingService] = None


def _get_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of text strings to embed.
    
    Returns:
        list[list[float]]: List of embedding vectors.
    """
    return _get_service().embed_texts(texts)


def embed_text(text: str) -> list[float]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Text string to embed.
    
    Returns:
        list[float]: Embedding vector.
    """
    return _get_service().embed_text(text)



