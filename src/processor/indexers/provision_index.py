#!/usr/bin/env python3
"""
Azure Cognitive Search Index Provisioning Script

Creates or updates the RAG search index with vector field configuration.
This script is idempotent - safe to run multiple times.

Usage:
    python -m src.processor.indexers.provision_index

Environment Variables:
    SEARCH_ENDPOINT: Azure Cognitive Search endpoint URL
    SEARCH_API_KEY: Azure Cognitive Search admin API key
"""

import logging
import os
import sys
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SearchableField,
    SimpleField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Index configuration constants
INDEX_NAME = "rag-documents"
VECTOR_DIMENSIONS = 1536  # text-embedding-ada-002 dimensions
VECTOR_PROFILE_NAME = "rag-vector-profile"
VECTOR_ALGORITHM_NAME = "rag-hnsw-algorithm"
SEMANTIC_CONFIG_NAME = "rag-semantic-config"


def get_index_schema() -> SearchIndex:
    """
    Define the search index schema with vector and semantic search support.
    
    Returns:
        SearchIndex: The index configuration object.
    """
    # Define vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=VECTOR_ALGORITHM_NAME,
                parameters={
                    "m": 4,  # Number of bi-directional links
                    "efConstruction": 400,  # Size of dynamic list during indexing
                    "efSearch": 500,  # Size of dynamic list during search
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE_NAME,
                algorithm_configuration_name=VECTOR_ALGORITHM_NAME,
            )
        ]
    )

    # Define semantic search configuration
    semantic_config = SemanticConfiguration(
        name=SEMANTIC_CONFIG_NAME,
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="fileName")],
        )
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Define index fields
    fields = [
        # Primary key - deterministic ID based on source path and chunk
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        # Main content field - searchable text
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="en.microsoft",
        ),
        # Vector embedding field
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
        # Source document path
        SimpleField(
            name="sourcePath",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        # Original file name
        SimpleField(
            name="fileName",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            sortable=True,
        ),
        # Chunk index within document
        SimpleField(
            name="chunkId",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        # Processing timestamp
        SimpleField(
            name="processedAt",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        # Additional metadata
        SimpleField(
            name="pageNumber",
            type=SearchFieldDataType.Int32,
            filterable=True,
        ),
        SimpleField(
            name="totalChunks",
            type=SearchFieldDataType.Int32,
            filterable=True,
        ),
    ]

    # Create the index
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    return index


def provision_index(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    index_name: Optional[str] = None,
) -> bool:
    """
    Create or update the search index.
    
    This operation is idempotent - if the index exists, it will be updated
    to match the schema. If it doesn't exist, it will be created.
    
    Args:
        endpoint: Azure Cognitive Search endpoint URL. 
                  Defaults to SEARCH_ENDPOINT environment variable.
        api_key: Azure Cognitive Search admin API key.
                 Defaults to SEARCH_API_KEY environment variable.
        index_name: Name of the index to create/update.
                    Defaults to INDEX_NAME constant.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    # Get configuration from environment if not provided
    endpoint = endpoint or os.getenv("SEARCH_ENDPOINT")
    api_key = api_key or os.getenv("SEARCH_API_KEY")
    index_name = index_name or INDEX_NAME

    if not endpoint:
        logger.error("SEARCH_ENDPOINT environment variable is required")
        return False

    if not api_key:
        logger.error("SEARCH_API_KEY environment variable is required")
        return False

    try:
        # Create the index client
        credential = AzureKeyCredential(api_key)
        client = SearchIndexClient(endpoint=endpoint, credential=credential)

        # Get the index schema
        index = get_index_schema()
        if index_name != INDEX_NAME:
            index.name = index_name

        # Check if index exists
        existing_indexes = [idx.name for idx in client.list_indexes()]
        
        if index.name in existing_indexes:
            logger.info(f"Index '{index.name}' exists, updating...")
            result = client.create_or_update_index(index)
            logger.info(f"Index '{result.name}' updated successfully")
        else:
            logger.info(f"Creating new index '{index.name}'...")
            result = client.create_index(index)
            logger.info(f"Index '{result.name}' created successfully")

        # Log index details
        logger.info(f"Index fields: {[f.name for f in result.fields]}")
        logger.info(f"Vector search profiles: {[p.name for p in result.vector_search.profiles]}")
        
        return True

    except Exception as e:
        logger.error(f"Failed to provision index: {e}")
        return False


def delete_index(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    index_name: Optional[str] = None,
) -> bool:
    """
    Delete the search index.
    
    Args:
        endpoint: Azure Cognitive Search endpoint URL.
        api_key: Azure Cognitive Search admin API key.
        index_name: Name of the index to delete.
    
    Returns:
        bool: True if successful or index doesn't exist, False on error.
    """
    endpoint = endpoint or os.getenv("SEARCH_ENDPOINT")
    api_key = api_key or os.getenv("SEARCH_API_KEY")
    index_name = index_name or INDEX_NAME

    if not endpoint or not api_key:
        logger.error("SEARCH_ENDPOINT and SEARCH_API_KEY are required")
        return False

    try:
        credential = AzureKeyCredential(api_key)
        client = SearchIndexClient(endpoint=endpoint, credential=credential)
        
        client.delete_index(index_name)
        logger.info(f"Index '{index_name}' deleted successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to delete index: {e}")
        return False


if __name__ == "__main__":
    # Run provisioning when executed directly
    success = provision_index()
    sys.exit(0 if success else 1)



