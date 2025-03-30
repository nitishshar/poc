import os
import shutil
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse, FileResponse

from app.config.settings import settings
from app.models.document import (
    DocumentModel, DocumentResponse, DocumentUploadResponse, DocumentStatus,
    ProcessingStep, StepStatus, TextChunk, TableInfo
)
from app.services.document_processor import (
    process_document, get_document, save_document, calculate_processing_progress,
    list_documents, delete_document as delete_doc_from_store
)
from app.services.embedding import query_embeddings, get_collection_info

router = APIRouter(prefix=settings.API_V1_STR)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    process_immediately: bool = Query(True, description="Start processing immediately after upload")
):
    """
    Upload a document for processing.
    
    Args:
        file: The document file to upload
        process_immediately: Whether to start processing immediately
        
    Returns:
        DocumentUploadResponse with document ID and status
    """
    # Check file extension
    filename = file.filename
    file_extension = os.path.splitext(filename)[1].lower()
    
    # Validate supported file types
    supported_extensions = ['.pdf', '.docx', '.doc', '.txt', '.csv', '.xlsx', '.xls']
    if file_extension not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Supported types: {', '.join(supported_extensions)}"
        )
    
    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create document model
    document = DocumentModel(
        filename=file_path,
        original_filename=filename,
        file_size=os.path.getsize(file_path),
        file_type=file_extension,
        status=DocumentStatus.UPLOADED
    )
    
    # Save to store
    save_document(document)
    
    # Start processing in background if requested
    if process_immediately:
        background_tasks.add_task(process_document, document.id)
    
    return DocumentUploadResponse(
        document_id=document.id,
        message="Document uploaded successfully",
        status=document.status
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_status(document_id: UUID = Path(..., description="The ID of the document")):
    """
    Get the processing status of a document.
    
    Args:
        document_id: The ID of the document
        
    Returns:
        DocumentResponse with status and metadata
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
    
    # Calculate processing progress
    processing_progress = calculate_processing_progress(document)
    
    # Determine current step
    current_step = None
    for step_info in document.processing_steps:
        if step_info.status == StepStatus.IN_PROGRESS:
            current_step = step_info.step
            break
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        file_type=document.file_type,
        upload_time=document.upload_time,
        status=document.status,
        metadata=document.metadata,
        processing_progress=processing_progress,
        current_step=current_step,
        error_message=document.error_message
    )


@router.post("/documents/{document_id}/process")
async def start_document_processing(
    document_id: UUID = Path(..., description="The ID of the document"),
    background_tasks: BackgroundTasks = None
):
    """
    Start or restart processing for a document.
    
    Args:
        document_id: The ID of the document
        
    Returns:
        JSON response with status
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
    
    if document.status == DocumentStatus.PROCESSING:
        return JSONResponse(
            status_code=200,
            content={"message": f"Document {document_id} is already being processed"}
        )
    
    # Reset status if previously failed
    if document.status == DocumentStatus.FAILED:
        document.status = DocumentStatus.UPLOADED
        document.error_message = None
        
        # Reset processing steps
        document.processing_steps = []
        
        # Save changes
        save_document(document)
    
    # Start processing in background
    background_tasks.add_task(process_document, document_id)
    
    return JSONResponse(
        status_code=202,
        content={"message": f"Processing started for document {document_id}"}
    )


@router.get("/documents/{document_id}/content", response_model=List[TextChunk])
async def get_document_content(
    document_id: UUID = Path(..., description="The ID of the document"),
    page: Optional[int] = Query(None, description="Filter by page number"),
    section: Optional[str] = Query(None, description="Filter by section title")
):
    """
    Get the processed content of a document.
    
    Args:
        document_id: The ID of the document
        page: Optional page number to filter by
        section: Optional section title to filter by
        
    Returns:
        List of text chunks
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
    
    if document.status != DocumentStatus.PROCESSED:
        raise HTTPException(
            status_code=400, 
            detail=f"Document content not available. Current status: {document.status}"
        )
    
    # Filter chunks if needed
    chunks = document.text_chunks
    
    if page is not None:
        chunks = [c for c in chunks if c.page_number == page]
    
    if section:
        chunks = [c for c in chunks if c.section_title and section.lower() in c.section_title.lower()]
    
    return chunks


@router.get("/documents/{document_id}/tables", response_model=List[TableInfo])
async def get_document_tables(
    document_id: UUID = Path(..., description="The ID of the document"),
    page: Optional[int] = Query(None, description="Filter by page number")
):
    """
    Get the tables extracted from a document.
    
    Args:
        document_id: The ID of the document
        page: Optional page number to filter by
        
    Returns:
        List of table information
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
    
    if document.status != DocumentStatus.PROCESSED:
        raise HTTPException(
            status_code=400, 
            detail=f"Document tables not available. Current status: {document.status}"
        )
    
    # Filter tables if needed
    tables = document.tables
    
    if page is not None:
        tables = [t for t in tables if t.page_number == page]
    
    return tables


@router.get("/documents/{document_id}/embeddings")
async def get_document_embeddings(
    document_id: UUID = Path(..., description="The ID of the document"),
    query: str = Query(..., description="Query text to search for"),
    limit: int = Query(5, description="Number of results to return"),
    page: Optional[int] = Query(None, description="Filter by page number")
):
    """
    Query the document embeddings.
    
    Args:
        document_id: The ID of the document
        query: Query text to search for
        limit: Number of results to return
        page: Optional page number to filter by
        
    Returns:
        List of matching chunks with scores
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
    
    if document.status != DocumentStatus.PROCESSED:
        raise HTTPException(
            status_code=400, 
            detail=f"Document embeddings not available. Current status: {document.status}"
        )
    
    if not document.embedding_collection_name:
        raise HTTPException(status_code=400, detail="Document embeddings not generated")
    
    # Prepare filters
    filters = {}
    if page is not None:
        filters["page_number"] = page
    
    # Query embeddings
    results = await query_embeddings(
        collection_name=document.embedding_collection_name,
        query_text=query,
        n_results=limit,
        filters=filters
    )
    
    # Get collection info
    collection_info = await get_collection_info(document.embedding_collection_name)
    
    return {
        "collection_info": collection_info,
        "results": results
    }


@router.get("/documents/{document_id}/original")
async def download_original_document(document_id: UUID = Path(..., description="The ID of the document")):
    """
    Download the original document.
    
    Args:
        document_id: The ID of the document
        
    Returns:
        The original document file
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
    
    if not os.path.exists(document.filename):
        raise HTTPException(status_code=404, detail="Original file not found")
    
    return FileResponse(
        path=document.filename,
        filename=document.original_filename,
        media_type="application/octet-stream"
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def get_all_documents():
    """
    Get a list of all documents.
    
    Returns:
        List of DocumentResponse objects
    """
    documents = list_documents()
    
    # Format response
    response = []
    for document in documents:
        # Calculate processing progress
        processing_progress = calculate_processing_progress(document)
        
        # Determine current step
        current_step = None
        for step_info in document.processing_steps:
            if step_info.status == StepStatus.IN_PROGRESS:
                current_step = step_info.step
                break
        
        response.append(DocumentResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            file_size=document.file_size,
            file_type=document.file_type,
            upload_time=document.upload_time,
            status=document.status,
            metadata=document.metadata,
            processing_progress=processing_progress,
            current_step=current_step,
            error_message=document.error_message
        ))
    
    return response


@router.delete("/documents/{document_id}")
async def delete_document(document_id: UUID = Path(..., description="The ID of the document")):
    """
    Delete a document.
    
    Args:
        document_id: The ID of the document to delete
        
    Returns:
        JSON response with status
    """
    document = get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
        
    try:
        # Remove physical file if it exists
        if os.path.exists(document.filename):
            os.remove(document.filename)
            
        # Remove document from store
        delete_doc_from_store(document_id)
        
        return JSONResponse(
            status_code=200,
            content={"message": f"Document {document_id} deleted successfully"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}") 