"""
Azure RAGcelerator - PDF Text Extractor

Extracts text content from PDF documents.
"""

import io
import logging
from typing import Optional

import PyPDF2
from PyPDF2.errors import PdfReadError

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text from PDF documents."""

    SUPPORTED_EXTENSIONS = {".pdf"}

    def __init__(self):
        """Initialize the PDF extractor."""
        pass

    def extract(self, content: bytes, file_name: str) -> str:
        """
        Extract text from PDF content.
        
        Args:
            content: Raw PDF file content as bytes.
            file_name: Original file name (for logging/error messages).
        
        Returns:
            str: Extracted text content.
        
        Raises:
            ValueError: If the file type is not supported.
            PdfReadError: If the PDF cannot be parsed.
        """
        # Validate file extension
        extension = self._get_extension(file_name)
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        logger.info(f"Extracting text from PDF: {file_name} ({len(content)} bytes)")

        try:
            # Parse PDF
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text_parts = []
            total_pages = len(reader.pages)
            
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    logger.debug(f"Extracted page {page_num}/{total_pages}")
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num} "
                        f"of {file_name}: {e}"
                    )
            
            full_text = "\n\n".join(text_parts)
            
            # Log extraction stats
            logger.info(
                f"Extracted {len(full_text)} characters from "
                f"{total_pages} pages in {file_name}"
            )

            if not full_text.strip():
                logger.warning(
                    f"No text content extracted from {file_name}. "
                    "The PDF may be image-based or encrypted."
                )

            return full_text

        except PdfReadError as e:
            logger.error(f"Failed to read PDF {file_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error extracting text from {file_name}: {e}")
            raise

    def extract_with_metadata(
        self, content: bytes, file_name: str
    ) -> tuple[str, dict]:
        """
        Extract text and metadata from PDF.
        
        Args:
            content: Raw PDF file content.
            file_name: Original file name.
        
        Returns:
            tuple: (extracted_text, metadata_dict)
        """
        pdf_file = io.BytesIO(content)
        reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract metadata
        metadata = {
            "page_count": len(reader.pages),
            "file_name": file_name,
        }
        
        if reader.metadata:
            if reader.metadata.title:
                metadata["title"] = reader.metadata.title
            if reader.metadata.author:
                metadata["author"] = reader.metadata.author
            if reader.metadata.subject:
                metadata["subject"] = reader.metadata.subject
            if reader.metadata.creator:
                metadata["creator"] = reader.metadata.creator

        # Extract text
        text = self.extract(content, file_name)
        
        return text, metadata

    @staticmethod
    def _get_extension(file_name: str) -> str:
        """Get lowercase file extension including the dot."""
        if "." in file_name:
            return "." + file_name.rsplit(".", 1)[1].lower()
        return ""


# Module-level convenience functions
_extractor: Optional[PDFExtractor] = None


def _get_extractor() -> PDFExtractor:
    """Get or create the global extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = PDFExtractor()
    return _extractor


def extract_text(content: bytes, file_name: str) -> str:
    """
    Extract text from a PDF document.
    
    Args:
        content: Raw PDF file content as bytes.
        file_name: Original file name.
    
    Returns:
        str: Extracted text content.
    
    Raises:
        ValueError: If the file type is not supported.
    """
    return _get_extractor().extract(content, file_name)


def is_supported(file_name: str) -> bool:
    """
    Check if a file type is supported.
    
    Args:
        file_name: File name to check.
    
    Returns:
        bool: True if the file type is supported.
    """
    extension = PDFExtractor._get_extension(file_name)
    return extension in PDFExtractor.SUPPORTED_EXTENSIONS



