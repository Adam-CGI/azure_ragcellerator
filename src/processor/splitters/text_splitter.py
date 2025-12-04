"""
Azure RAGcelerator - Text Splitter

Splits long text into overlapping chunks for embedding.
"""

import logging
from typing import Optional

from ..config import get_settings
from ..models import Chunk

logger = logging.getLogger(__name__)


class TextSplitter:
    """
    Recursive character-based text splitter.
    
    Splits text into chunks of approximately target_chunk_size characters
    with overlap between consecutive chunks.
    """

    # Separators to try, in order of preference
    DEFAULT_SEPARATORS = [
        "\n\n",  # Paragraph breaks
        "\n",    # Line breaks
        ". ",    # Sentence endings
        "! ",    # Exclamation points
        "? ",    # Question marks
        "; ",    # Semicolons
        ", ",    # Commas
        " ",     # Spaces
        "",      # Character-by-character (last resort)
    ]

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[list[str]] = None,
    ):
        """
        Initialize the text splitter.
        
        Args:
            chunk_size: Target size for each chunk. Defaults to settings.
            chunk_overlap: Overlap between chunks. Defaults to settings.
            separators: List of separators to try, in order.
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"Chunk overlap ({self.chunk_overlap}) must be less than "
                f"chunk size ({self.chunk_size})"
            )

    def split(
        self,
        text: str,
        source_path: str,
        file_name: str,
    ) -> list[Chunk]:
        """
        Split text into chunks.
        
        Args:
            text: The text to split.
            source_path: Source document path.
            file_name: Source file name.
        
        Returns:
            list[Chunk]: List of text chunks.
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for splitting: {file_name}")
            return []

        # Clean the text
        text = text.strip()
        
        # Split into raw chunks
        raw_chunks = self._split_text(text, self.separators)
        
        # Merge small chunks and ensure overlap
        merged_chunks = self._merge_chunks(raw_chunks)
        
        # Create Chunk objects
        total_chunks = len(merged_chunks)
        chunks = []
        
        for i, chunk_text in enumerate(merged_chunks):
            if chunk_text.strip():  # Skip empty chunks
                chunk = Chunk(
                    chunk_id=i,
                    content=chunk_text.strip(),
                    source_path=source_path,
                    file_name=file_name,
                    total_chunks=total_chunks,
                )
                chunks.append(chunk)

        logger.info(
            f"Split {file_name} into {len(chunks)} chunks "
            f"(avg {sum(len(c.content) for c in chunks) // max(len(chunks), 1)} chars)"
        )

        return chunks

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """
        Recursively split text using separators.
        
        Args:
            text: Text to split.
            separators: List of separators to try.
        
        Returns:
            list[str]: Split text segments.
        """
        if not separators:
            # No more separators, split character by character
            return self._split_by_size(text)

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            # Character-by-character split
            return self._split_by_size(text)

        if separator not in text:
            # Try next separator
            return self._split_text(text, remaining_separators)

        # Split by current separator
        parts = text.split(separator)
        
        result = []
        for part in parts:
            if len(part) <= self.chunk_size:
                # Add separator back except for last part
                result.append(part)
            else:
                # Recursively split large parts
                sub_parts = self._split_text(part, remaining_separators)
                result.extend(sub_parts)

        return result

    def _split_by_size(self, text: str) -> list[str]:
        """Split text into chunks of maximum chunk_size."""
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunks.append(text[i:i + self.chunk_size])
        return chunks

    def _merge_chunks(self, chunks: list[str]) -> list[str]:
        """
        Merge chunks to meet size requirements and add overlap.
        
        Args:
            chunks: Raw text chunks.
        
        Returns:
            list[str]: Merged chunks with overlap.
        """
        if not chunks:
            return []

        merged = []
        current_chunk = ""
        
        for chunk in chunks:
            # Check if adding this chunk would exceed size
            if current_chunk and len(current_chunk) + len(chunk) + 1 > self.chunk_size:
                # Save current chunk
                merged.append(current_chunk)
                
                # Start new chunk with overlap from previous
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + " " + chunk
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += " " + chunk
                else:
                    current_chunk = chunk

        # Don't forget the last chunk
        if current_chunk:
            merged.append(current_chunk)

        return merged


# Module-level convenience function
def split_text_to_chunks(
    text: str,
    source_path: str,
    file_name: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[Chunk]:
    """
    Split text into chunks.
    
    Args:
        text: The text to split.
        source_path: Source document path.
        file_name: Source file name.
        chunk_size: Optional custom chunk size.
        chunk_overlap: Optional custom chunk overlap.
    
    Returns:
        list[Chunk]: List of text chunks.
    """
    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split(text, source_path, file_name)



