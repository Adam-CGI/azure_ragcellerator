"""
Azure RAGcelerator - UI Configuration

Pydantic-based configuration management for the Streamlit UI.
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

    # Azure Cognitive Search
    search_endpoint: str = Field(
        default="",
        description="Azure Cognitive Search endpoint URL",
    )
    search_api_key: str = Field(
        default="",
        description="Azure Cognitive Search API key",
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
    chat_model: str = Field(
        default="gpt-35-turbo",
        description="Chat model deployment name",
    )

    # UI Settings
    app_title: str = Field(
        default="Azure RAGcelerator",
        description="Application title",
    )
    max_search_results: int = Field(
        default=10,
        description="Maximum number of search results to return",
    )
    max_context_chunks: int = Field(
        default=5,
        description="Maximum chunks to include in RAG context",
    )

    def validate_required(self) -> list[str]:
        """
        Validate that all required settings are present.
        
        Returns:
            List of missing required field names.
        """
        missing = []
        
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
    
    Returns:
        Settings: The application settings.
    """
    return Settings()



