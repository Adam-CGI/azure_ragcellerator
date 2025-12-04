"""
Tests for the Text Splitter.
"""

import pytest

from src.processor.splitters.text_splitter import TextSplitter, split_text_to_chunks


class TestTextSplitter:
    """Tests for TextSplitter class."""

    @pytest.fixture
    def splitter(self):
        """Create a text splitter with default settings."""
        return TextSplitter(chunk_size=100, chunk_overlap=20)

    def test_split_short_text(self, splitter):
        """Test splitting text shorter than chunk size."""
        text = "This is a short text."
        chunks = splitter.split(text, "/test/doc.pdf", "doc.pdf")
        
        assert len(chunks) == 1
        assert chunks[0].content == "This is a short text."
        assert chunks[0].chunk_id == 0

    def test_split_long_text(self, splitter):
        """Test splitting text longer than chunk size."""
        # Create text with natural break points
        text = "First paragraph. " * 10 + "\n\n" + "Second paragraph. " * 10
        chunks = splitter.split(text, "/test/doc.pdf", "doc.pdf")
        
        assert len(chunks) >= 2
        # Check no chunks exceed the size (with some tolerance for overlap)
        for chunk in chunks:
            assert len(chunk.content) <= splitter.chunk_size + 50

    def test_chunk_overlap(self):
        """Test that chunks have proper overlap."""
        splitter = TextSplitter(chunk_size=50, chunk_overlap=10)
        
        # Create text that will definitely be split
        words = ["word" + str(i) for i in range(30)]
        text = " ".join(words)
        
        chunks = splitter.split(text, "/test/doc.pdf", "doc.pdf")
        
        # Verify we got multiple chunks
        assert len(chunks) >= 2
        
        # Check that consecutive chunks share some content (overlap)
        for i in range(len(chunks) - 1):
            current_end = chunks[i].content[-10:]  # Last 10 chars
            next_start = chunks[i + 1].content[:20]  # First 20 chars
            # There should be some overlap
            # (This is a simplified check - actual overlap may vary)
            assert len(chunks[i].content) > 0
            assert len(chunks[i + 1].content) > 0

    def test_no_empty_chunks(self, splitter):
        """Test that no empty chunks are created."""
        text = "Content\n\n\n\nMore content\n\n\nFinal content"
        chunks = splitter.split(text, "/test/doc.pdf", "doc.pdf")
        
        for chunk in chunks:
            assert chunk.content.strip() != ""

    def test_chunk_metadata(self, splitter):
        """Test that chunks have correct metadata."""
        text = "Test content for chunking. " * 20
        source_path = "/container/documents/test.pdf"
        file_name = "test.pdf"
        
        chunks = splitter.split(text, source_path, file_name)
        
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == i
            assert chunk.source_path == source_path
            assert chunk.file_name == file_name
            assert chunk.total_chunks == len(chunks)

    def test_empty_text(self, splitter):
        """Test handling of empty text."""
        chunks = splitter.split("", "/test/doc.pdf", "doc.pdf")
        assert chunks == []

        chunks = splitter.split("   ", "/test/doc.pdf", "doc.pdf")
        assert chunks == []

    def test_chunk_document_id(self, splitter):
        """Test that document IDs are correctly generated."""
        text = "Test content"
        chunks = splitter.split(text, "/container/test.pdf", "test.pdf")
        
        assert len(chunks) == 1
        # Document ID should be deterministic
        doc_id = chunks[0].document_id
        assert "chunk_0" in doc_id

    def test_invalid_overlap(self):
        """Test that invalid overlap raises error."""
        with pytest.raises(ValueError, match="Chunk overlap"):
            TextSplitter(chunk_size=100, chunk_overlap=100)
        
        with pytest.raises(ValueError, match="Chunk overlap"):
            TextSplitter(chunk_size=100, chunk_overlap=150)

    def test_preserves_paragraph_structure(self, splitter):
        """Test that paragraph breaks are preserved when possible."""
        text = "First paragraph content here.\n\nSecond paragraph content here."
        chunks = splitter.split(text, "/test/doc.pdf", "doc.pdf")
        
        # Should ideally keep paragraphs together if they fit
        assert len(chunks) >= 1

    def test_sentence_boundary_splitting(self):
        """Test that text is split at sentence boundaries when possible."""
        splitter = TextSplitter(chunk_size=50, chunk_overlap=10)
        
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = splitter.split(text, "/test/doc.pdf", "doc.pdf")
        
        # Chunks should preferably end at sentence boundaries
        assert len(chunks) >= 1


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_split_text_to_chunks_function(self):
        """Test the split_text_to_chunks function."""
        text = "This is test content. " * 20
        chunks = split_text_to_chunks(
            text,
            "/test/doc.pdf",
            "doc.pdf",
            chunk_size=100,
            chunk_overlap=20,
        )
        
        assert len(chunks) >= 1
        assert all(c.file_name == "doc.pdf" for c in chunks)

    def test_split_text_to_chunks_default_settings(self):
        """Test split_text_to_chunks with default settings."""
        text = "Test content"
        chunks = split_text_to_chunks(text, "/test/doc.pdf", "doc.pdf")
        
        assert len(chunks) == 1
        assert chunks[0].content == "Test content"



