"""
Azure RAGcelerator - Data Models

Data classes for documents, chunks, and processing results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Document:
    """Represents a source document."""
    
    source_path: str
    file_name: str
    content: bytes
    content_type: str = "application/pdf"
    metadata: dict = field(default_factory=dict)
    uploaded_at: Optional[datetime] = None

    @property
    def text_content(self) -> Optional[str]:
        """Get content as text if possible."""
        try:
            return self.content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def __repr__(self) -> str:
        return f"Document(file_name={self.file_name!r}, size={len(self.content)} bytes)"


@dataclass
class Chunk:
    """Represents a text chunk from a document."""
    
    chunk_id: int
    content: str
    source_path: str
    file_name: str
    page_number: Optional[int] = None
    total_chunks: Optional[int] = None
    embedding: Optional[list[float]] = None

    @property
    def document_id(self) -> str:
        """
        Generate a deterministic document ID for this chunk.
        Format: {source_path}#chunk_{chunk_id}
        """
        # Sanitize source path for use in ID
        safe_path = self.source_path.replace("/", "_").replace("\\", "_")
        return f"{safe_path}#chunk_{self.chunk_id}"

    def to_search_document(self, processed_at: Optional[datetime] = None) -> dict:
        """
        Convert chunk to a search document for indexing.
        
        Args:
            processed_at: Processing timestamp. Defaults to current time.
        
        Returns:
            dict: Document ready for Azure Cognitive Search indexing.
        """
        if processed_at is None:
            processed_at = datetime.utcnow()

        doc = {
            "id": self.document_id,
            "content": self.content,
            "sourcePath": self.source_path,
            "fileName": self.file_name,
            "chunkId": self.chunk_id,
            "processedAt": processed_at.isoformat() + "Z",
        }

        if self.embedding is not None:
            doc["contentVector"] = self.embedding

        if self.page_number is not None:
            doc["pageNumber"] = self.page_number

        if self.total_chunks is not None:
            doc["totalChunks"] = self.total_chunks

        return doc

    def __repr__(self) -> str:
        return (
            f"Chunk(id={self.chunk_id}, file={self.file_name!r}, "
            f"len={len(self.content)}, has_embedding={self.embedding is not None})"
        )


@dataclass
class ProcessingResult:
    """Result of document processing."""
    
    source_path: str
    file_name: str
    success: bool
    chunks_created: int = 0
    chunks_indexed: int = 0
    error_message: Optional[str] = None
    processing_time_ms: float = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "source_path": self.source_path,
            "file_name": self.file_name,
            "success": self.success,
            "chunks_created": self.chunks_created,
            "chunks_indexed": self.chunks_indexed,
            "error_message": self.error_message,
            "processing_time_ms": self.processing_time_ms,
        }


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
    def from_search_document(cls, doc: dict, score: float) -> "SearchResult":
        """
        Create SearchResult from a Cognitive Search document.
        
        Args:
            doc: The search document dictionary.
            score: The relevance score.
        
        Returns:
            SearchResult: The parsed result.
        """
        return cls(
            content=doc.get("content", ""),
            file_name=doc.get("fileName", ""),
            source_path=doc.get("sourcePath", ""),
            score=score,
            chunk_id=doc.get("chunkId", 0),
            highlights=doc.get("@search.highlights", {}).get("content"),
        )



