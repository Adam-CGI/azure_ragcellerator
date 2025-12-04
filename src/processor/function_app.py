"""
Azure RAGcelerator - Azure Function App

Event Grid triggered document processing pipeline.
"""

import json
import logging
import time
from typing import Optional

import azure.functions as func

from .config import get_settings
from .embeddings.azure_openai import EmbeddingService
from .extractors.pdf_extractor import PDFExtractor, is_supported
from .indexers.cognitive_search import SearchIndexer
from .models import ProcessingResult
from .splitters.text_splitter import TextSplitter
from .storage.blob_service import BlobService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the Function App
app = func.FunctionApp()


class DocumentProcessor:
    """Processes documents through the RAG pipeline."""

    def __init__(
        self,
        blob_service: Optional[BlobService] = None,
        extractor: Optional[PDFExtractor] = None,
        splitter: Optional[TextSplitter] = None,
        embedding_service: Optional[EmbeddingService] = None,
        indexer: Optional[SearchIndexer] = None,
    ):
        """
        Initialize the document processor with optional dependency injection.
        
        Args:
            blob_service: Blob storage service.
            extractor: PDF text extractor.
            splitter: Text splitter.
            embedding_service: Embedding generation service.
            indexer: Search indexer.
        """
        self.blob_service = blob_service or BlobService()
        self.extractor = extractor or PDFExtractor()
        self.splitter = splitter or TextSplitter()
        self.embedding_service = embedding_service or EmbeddingService()
        self.indexer = indexer or SearchIndexer()

    def process(self, blob_url: str) -> ProcessingResult:
        """
        Process a document through the complete pipeline.
        
        Pipeline steps:
        1. Download blob from storage
        2. Extract text from PDF
        3. Split text into chunks
        4. Generate embeddings
        5. Upsert to search index
        
        Args:
            blob_url: URL or path to the blob to process.
        
        Returns:
            ProcessingResult: Result of the processing.
        """
        start_time = time.time()
        file_name = blob_url.split("/")[-1]
        
        logger.info(f"Starting document processing: {file_name}")

        try:
            # Validate file type
            if not is_supported(file_name):
                return ProcessingResult(
                    source_path=blob_url,
                    file_name=file_name,
                    success=False,
                    error_message=f"Unsupported file type: {file_name}",
                    processing_time_ms=(time.time() - start_time) * 1000,
                )

            # Step 1: Download blob
            logger.info(f"[1/5] Downloading blob: {blob_url}")
            document = self.blob_service.download_document(blob_url)
            logger.info(f"Downloaded {len(document.content)} bytes")

            # Step 2: Extract text
            logger.info(f"[2/5] Extracting text from: {file_name}")
            text = self.extractor.extract(document.content, file_name)
            logger.info(f"Extracted {len(text)} characters")

            if not text.strip():
                return ProcessingResult(
                    source_path=blob_url,
                    file_name=file_name,
                    success=False,
                    error_message="No text content extracted from document",
                    processing_time_ms=(time.time() - start_time) * 1000,
                )

            # Step 3: Split into chunks
            logger.info(f"[3/5] Splitting text into chunks")
            chunks = self.splitter.split(text, blob_url, file_name)
            logger.info(f"Created {len(chunks)} chunks")

            if not chunks:
                return ProcessingResult(
                    source_path=blob_url,
                    file_name=file_name,
                    success=False,
                    error_message="No chunks created from document",
                    processing_time_ms=(time.time() - start_time) * 1000,
                )

            # Step 4: Generate embeddings
            logger.info(f"[4/5] Generating embeddings for {len(chunks)} chunks")
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.embed_texts(chunk_texts)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # Step 5: Delete existing chunks and upsert new ones
            logger.info(f"[5/5] Indexing chunks to search")
            self.indexer.delete_by_source_path(blob_url)
            success_count, failed_count = self.indexer.upsert_chunks(chunks, embeddings)
            logger.info(f"Indexed {success_count} chunks, {failed_count} failed")

            processing_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"Document processing complete: {file_name} "
                f"({len(chunks)} chunks in {processing_time:.0f}ms)"
            )

            return ProcessingResult(
                source_path=blob_url,
                file_name=file_name,
                success=failed_count == 0,
                chunks_created=len(chunks),
                chunks_indexed=success_count,
                error_message=f"{failed_count} chunks failed to index" if failed_count else None,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Error processing document {file_name}: {e}", exc_info=True)
            return ProcessingResult(
                source_path=blob_url,
                file_name=file_name,
                success=False,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )


# Global processor instance
_processor: Optional[DocumentProcessor] = None


def get_processor() -> DocumentProcessor:
    """Get or create the document processor."""
    global _processor
    if _processor is None:
        # Validate configuration
        settings = get_settings()
        missing = settings.validate_required()
        if missing:
            raise RuntimeError(
                f"Missing required configuration: {', '.join(missing)}"
            )
        _processor = DocumentProcessor()
    return _processor


@app.function_name(name="process_document")
@app.event_grid_trigger(arg_name="event")
def process_document(event: func.EventGridEvent) -> None:
    """
    Event Grid triggered function to process uploaded documents.
    
    Triggered when a blob is created in the 'documents' container.
    
    Args:
        event: The Event Grid event containing blob information.
    """
    logger.info(f"Received Event Grid event: {event.id}")
    logger.info(f"Event type: {event.event_type}")
    logger.info(f"Event subject: {event.subject}")

    try:
        # Parse event data
        event_data = event.get_json()
        blob_url = event_data.get("url")
        
        if not blob_url:
            logger.error("No blob URL in event data")
            return

        logger.info(f"Processing blob: {blob_url}")

        # Process the document
        processor = get_processor()
        result = processor.process(blob_url)

        # Log result
        if result.success:
            logger.info(
                f"Successfully processed {result.file_name}: "
                f"{result.chunks_indexed} chunks indexed in {result.processing_time_ms:.0f}ms"
            )
        else:
            logger.error(
                f"Failed to process {result.file_name}: {result.error_message}"
            )

    except Exception as e:
        logger.error(f"Error in Event Grid handler: {e}", exc_info=True)
        raise


# HTTP trigger for testing/manual processing
@app.function_name(name="process_document_http")
@app.route(route="process", methods=["POST"])
def process_document_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for manual document processing.
    
    Request body should contain: {"blob_url": "container/path/to/file.pdf"}
    
    Args:
        req: HTTP request with blob URL in body.
    
    Returns:
        HTTP response with processing result.
    """
    logger.info("Received HTTP request for document processing")

    try:
        body = req.get_json()
        blob_url = body.get("blob_url")
        
        if not blob_url:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'blob_url' in request body"}),
                status_code=400,
                mimetype="application/json",
            )

        # Process the document
        processor = get_processor()
        result = processor.process(blob_url)

        return func.HttpResponse(
            json.dumps(result.to_dict()),
            status_code=200 if result.success else 500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error in HTTP handler: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )


# Health check endpoint
@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.
    
    Returns:
        HTTP response with health status.
    """
    return func.HttpResponse(
        json.dumps({"status": "healthy"}),
        status_code=200,
        mimetype="application/json",
    )



