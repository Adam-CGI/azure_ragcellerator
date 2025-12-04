# Azure RAGcelerator - Extractors Package
"""
Text extraction from various document formats.
"""

from .pdf_extractor import PDFExtractor, extract_text

__all__ = [
    "PDFExtractor",
    "extract_text",
]



