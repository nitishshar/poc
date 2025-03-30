import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from app.config.settings import settings
from app.models.document import (
    DocumentModel, DocumentStatus, ProcessingStep,
    ProcessingStepInfo, StepStatus, TextChunk, TableInfo
)
from app.services.extractors import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    extract_text_from_csv,
    perform_ocr,
    extract_tables
)
from app.services.metadata import extract_metadata
from app.services.chunking import chunk_text
from app.services.embedding import generate_embeddings

logger = logging.getLogger(__name__)

# Dictionary to track processing documents
document_store: Dict[UUID, DocumentModel] = {}


async def process_document(document_id: UUID) -> DocumentModel:
    """
    Process a document asynchronously through the entire processing pipeline.
    
    Args:
        document_id: UUID of the document to process
        
    Returns:
        DocumentModel with updated processing information
    """
    document = document_store.get(document_id)
    if not document:
        logger.error(f"Document with ID {document_id} not found")
        return None
    
    try:
        # Update document status
        document.status = DocumentStatus.PROCESSING
        _update_document_store(document)
        
        # Initialize processing steps if not already initialized
        if not document.processing_steps:
            document.processing_steps = [
                ProcessingStepInfo(step=ProcessingStep.TEXT_EXTRACTION),
                ProcessingStepInfo(step=ProcessingStep.OCR),
                ProcessingStepInfo(step=ProcessingStep.TABLE_DETECTION),
                ProcessingStepInfo(step=ProcessingStep.TEXT_CHUNKING),
                ProcessingStepInfo(step=ProcessingStep.EMBEDDING_GENERATION),
                ProcessingStepInfo(step=ProcessingStep.METADATA_EXTRACTION),
                ProcessingStepInfo(step=ProcessingStep.COMPLETED)
            ]
            _update_document_store(document)
        
        # Text extraction
        await _update_step_status(document, ProcessingStep.TEXT_EXTRACTION, StepStatus.IN_PROGRESS)
        extracted_text, needs_ocr = await _extract_text(document)
        await _update_step_status(document, ProcessingStep.TEXT_EXTRACTION, StepStatus.COMPLETED)
        
        # OCR if needed
        if needs_ocr:
            await _update_step_status(document, ProcessingStep.OCR, StepStatus.IN_PROGRESS)
            ocr_text = await perform_ocr(document.filename)
            extracted_text += " " + ocr_text if extracted_text else ocr_text
            await _update_step_status(document, ProcessingStep.OCR, StepStatus.COMPLETED)
        else:
            await _update_step_status(document, ProcessingStep.OCR, StepStatus.SKIPPED)
        
        # Table detection and extraction
        await _update_step_status(document, ProcessingStep.TABLE_DETECTION, StepStatus.IN_PROGRESS)
        tables = await _extract_tables(document)
        document.tables = tables
        await _update_step_status(document, ProcessingStep.TABLE_DETECTION, StepStatus.COMPLETED)
        
        # Text chunking
        await _update_step_status(document, ProcessingStep.TEXT_CHUNKING, StepStatus.IN_PROGRESS)
        text_chunks = await _chunk_text(extracted_text, document)
        document.text_chunks = text_chunks
        await _update_step_status(document, ProcessingStep.TEXT_CHUNKING, StepStatus.COMPLETED)
        
        # Metadata extraction
        await _update_step_status(document, ProcessingStep.METADATA_EXTRACTION, StepStatus.IN_PROGRESS)
        metadata = await extract_metadata(document.filename, document.file_type)
        document.metadata = metadata
        await _update_step_status(document, ProcessingStep.METADATA_EXTRACTION, StepStatus.COMPLETED)
        
        # Embedding generation
        await _update_step_status(document, ProcessingStep.EMBEDDING_GENERATION, StepStatus.IN_PROGRESS)
        collection_name = await generate_embeddings(document)
        document.embedding_collection_name = collection_name
        await _update_step_status(document, ProcessingStep.EMBEDDING_GENERATION, StepStatus.COMPLETED)
        
        # Mark process as completed
        await _update_step_status(document, ProcessingStep.COMPLETED, StepStatus.COMPLETED)
        document.status = DocumentStatus.PROCESSED
        
    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {str(e)}")
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)
        
        # Mark current step as failed
        current_step = next((step for step in document.processing_steps 
                            if step.status == StepStatus.IN_PROGRESS), None)
        if current_step:
            current_step.status = StepStatus.FAILED
            current_step.error = str(e)
            current_step.end_time = datetime.now()
    
    _update_document_store(document)
    return document


async def _extract_text(document: DocumentModel) -> Tuple[str, bool]:
    """Extract text from a document based on its file type."""
    file_path = document.filename
    file_type = document.file_type.lower()
    
    extracted_text = ""
    needs_ocr = False
    
    try:
        if file_type.endswith('pdf'):
            extracted_text, needs_ocr = await extract_text_from_pdf(file_path)
        elif file_type.endswith(('docx', 'doc')):
            extracted_text = await extract_text_from_docx(file_path)
        elif file_type.endswith('txt'):
            extracted_text = await extract_text_from_txt(file_path)
        elif file_type.endswith(('csv', 'xlsx', 'xls')):
            extracted_text = await extract_text_from_csv(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_type}. Will attempt OCR.")
            needs_ocr = True
            
        if not extracted_text and not needs_ocr:
            needs_ocr = True
            
    except Exception as e:
        logger.exception(f"Error extracting text from {file_path}: {str(e)}")
        needs_ocr = True
        
    return extracted_text, needs_ocr


async def _extract_tables(document: DocumentModel) -> List[TableInfo]:
    """Extract tables from a document."""
    if not settings.EXTRACT_TABLES:
        return []
    
    file_path = document.filename
    file_type = document.file_type.lower()
    
    try:
        tables = await extract_tables(file_path, file_type)
        return tables
    except Exception as e:
        logger.exception(f"Error extracting tables from {file_path}: {str(e)}")
        return []


async def _chunk_text(text: str, document: DocumentModel) -> List[TextChunk]:
    """Chunk the extracted text."""
    try:
        return await chunk_text(
            text, 
            settings.DEFAULT_CHUNK_SIZE, 
            settings.DEFAULT_CHUNK_OVERLAP,
            file_path=document.filename
        )
    except Exception as e:
        logger.exception(f"Error chunking text: {str(e)}")
        # Return a single chunk with the entire text as fallback
        return [TextChunk(text=text)]


async def _update_step_status(
    document: DocumentModel, 
    step: ProcessingStep, 
    status: StepStatus,
    progress: float = 0.0,
    message: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """Update the status of a processing step."""
    step_info = next((s for s in document.processing_steps if s.step == step), None)
    
    if step_info:
        step_info.status = status
        
        if status == StepStatus.IN_PROGRESS and not step_info.start_time:
            step_info.start_time = datetime.now()
            
        if status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED) and not step_info.end_time:
            step_info.end_time = datetime.now()
            
        if progress > 0:
            step_info.progress = progress
            
        if message:
            step_info.message = message
            
        if error:
            step_info.error = error
    
    _update_document_store(document)


def _update_document_store(document: DocumentModel) -> None:
    """Update the document in the document store."""
    document_store[document.id] = document


def get_document(document_id: UUID) -> Optional[DocumentModel]:
    """Get a document from the document store."""
    return document_store.get(document_id)


def list_documents() -> List[DocumentModel]:
    """Get all documents from the document store.
    
    Returns:
        List of all document models
    """
    return list(document_store.values())


def save_document(document: DocumentModel) -> DocumentModel:
    """Save a document to the document store."""
    document_store[document.id] = document
    return document


def calculate_processing_progress(document: DocumentModel) -> float:
    """Calculate the overall processing progress as a value from 0 to 1."""
    if document.status == DocumentStatus.PROCESSED:
        return 1.0
    
    if document.status == DocumentStatus.UPLOADED:
        return 0.0
    
    if not document.processing_steps:
        return 0.0
    
    # Filter out the COMPLETED step which is a meta-step
    active_steps = [step for step in document.processing_steps if step.step != ProcessingStep.COMPLETED]
    
    if not active_steps:
        return 0.0
    
    total_steps = len(active_steps)
    completed_steps = sum(1 for step in active_steps 
                         if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
    
    in_progress_step = next((step for step in active_steps 
                             if step.status == StepStatus.IN_PROGRESS), None)
    
    if not in_progress_step:
        return completed_steps / total_steps
    
    # Add the progress of the current step
    current_step_weight = 1 / total_steps
    return (completed_steps / total_steps) + (in_progress_step.progress * current_step_weight) 