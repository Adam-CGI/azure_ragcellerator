"""
Azure RAGcelerator - Processor Configuration

Pydantic-based configuration management for the document processing pipeline.
All settings are loaded from environment variables.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure Storage
    storage_connection_string: str = Field(
        default="",
        description="Azure Storage connection string",
    )
    documents_container_name: str = Field(
        default="documents",
        description="Name of the container for document uploads",
    )

    # Azure Cognitive Search
    search_endpoint: str = Field(
        default="",
        description="Azure Cognitive Search endpoint URL",
    )
    search_api_key: str = Field(
        default="",
        description="Azure Cognitive Search admin API key",
    )
    search_index_name: str = Field(
        default="rag-documents",
        description="Name of the search index",
    )

    # Azure OpenAI
    openai_endpoint: str = Field(
        default="",
        description="Azure OpenAI endpoint URL",
    )
    openai_api_key: str = Field(
        default="",
        description="Azure OpenAI API key",
    )
    openai_api_version: str = Field(
        default="2024-02-01",
        description="Azure OpenAI API version",
    )
    embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="Embedding model deployment name",
    )

    # Processing settings
    chunk_size: int = Field(
        default=1000,
        description="Target size for text chunks",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between consecutive chunks",
    )
    embedding_batch_size: int = Field(
        default=16,
        description="Number of texts to embed in a single API call",
    )

    # Application Insights (optional)
    applicationinsights_connection_string: Optional[str] = Field(
        default=None,
        description="Application Insights connection string for logging",
    )

    def validate_required(self) -> list[str]:
        """
        Validate that all required settings are present.
        
        Returns:
            List of missing required field names.
        """
        missing = []
        
        if not self.storage_connection_string:
            missing.append("STORAGE_CONNECTION_STRING")
        if not self.search_endpoint:
            missing.append("SEARCH_ENDPOINT")
        if not self.search_api_key:
            missing.append("SEARCH_API_KEY")
        if not self.openai_endpoint:
            missing.append("OPENAI_ENDPOINT")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")

        return missing


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: The application settings.
    """
    return Settings()


def get_settings_uncached() -> Settings:
    """
    Get a fresh settings instance (not cached).
    Useful for testing or when environment changes.
    
    Returns:
        Settings: The application settings.
    """
    return Settings()



