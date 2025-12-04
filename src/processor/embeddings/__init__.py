# Azure RAGcelerator - Embeddings Package
"""
Vector embedding generation using Azure OpenAI.
"""

from .azure_openai import EmbeddingService, embed_texts

__all__ = [
    "EmbeddingService",
    "embed_texts",
]



