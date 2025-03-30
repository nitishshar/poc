import os
import shutil
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Query, Path as PathParam, Form, Body
from fastapi.responses import JSONResponse, FileResponse

from app.config.settings import settings
from app.models.document import (
    DocumentModel, DocumentResponse, DocumentUploadResponse, DocumentStatus,
    ProcessingStep, StepStatus, TextChunk, TableInfo, DocumentUploadRequest
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
    file: Optional[UploadFile] = File(None),
    file_path: Optional[str] = Form(None),
    file_url: Optional[str] = Form(None),
    process_immediately: bool = Query(True, description="Start processing immediately after upload")
):
    """
    Upload a document for processing.
    
    Args:
        file: The document file to upload
        file_path: Path to a local file on the server
        file_url: URL to download a file from
        process_immediately: Whether to start processing immediately
        
    Returns:
        DocumentUploadResponse with document ID and status
    """
    # Check if at least one source is provided
    if not any([file, file_path, file_url]):
        raise HTTPException(
            status_code=400,
            detail="You must provide either a file upload, a file path, or a file URL"
        )
    
    # Prioritize file upload, then file path, then URL
    if file:
        # File upload handling
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
        
    elif file_path:
        # Local file path handling
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found at path: {file_path}")
        
        filename = os.path.basename(file_path)
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
        destination_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Copy the file
        try:
            shutil.copy2(file_path, destination_path)
            file_path = destination_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error copying file: {str(e)}")
        
    else:  # file_url must be provided based on initial check
        # URL file handling
        try:
            # Extract filename from URL
            filename = os.path.basename(file_url)
            if not filename:
                filename = f"download_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            file_extension = os.path.splitext(filename)[1].lower()
            if not file_extension:
                # If no extension in URL, default to .pdf
                filename += ".pdf"
                file_extension = ".pdf"
            
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
            
            # Download the file
            urllib.request.urlretrieve(file_url, file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error downloading file from URL: {str(e)}")
    
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


@router.post("/documents/upload-by-path", response_model=DocumentUploadResponse)
async def upload_document_by_path(
    background_tasks: BackgroundTasks,
    upload_request: DocumentUploadRequest
):
    """
    Upload a document for processing using a local file path or URL.
    
    This is an alternative endpoint for systems that cannot use form-based uploads.
    
    Args:
        upload_request: Contains file_path or file_url
        
    Returns:
        DocumentUploadResponse with document ID and status
    """
    # Check if at least one source is provided
    if not any([upload_request.file_path, upload_request.file_url]):
        raise HTTPException(
            status_code=400,
            detail="You must provide either a file path or a file URL"
        )
    
    if upload_request.file_path:
        file_path = upload_request.file_path
        process_immediately = upload_request.process_immediately
    else:
        file_path = None
        file_url = upload_request.file_url
        process_immediately = upload_request.process_immediately
    
    # Use the existing endpoint
    return await upload_document(
        background_tasks=background_tasks,
        file=None,
        file_path=file_path,
        file_url=file_url if not file_path else None,
        process_immediately=process_immediately
    )


@router.post("/documents/batch-upload", response_model=List[DocumentUploadResponse])
async def batch_upload_documents(
    background_tasks: BackgroundTasks,
    batch_request: List[DocumentUploadRequest]
):
    """
    Process multiple documents by path or URL in a single request.
    
    Args:
        batch_request: List of DocumentUploadRequest objects with file paths or URLs
        
    Returns:
        List of DocumentUploadResponse with document IDs and statuses
    """
    if not batch_request:
        raise HTTPException(
            status_code=400,
            detail="No documents provided for processing"
        )
    
    responses = []
    
    for request in batch_request:
        try:
            # Process each document using the existing upload_document function
            result = await upload_document(
                background_tasks=background_tasks,
                file=None,
                file_path=request.file_path,
                file_url=request.file_url,
                process_immediately=request.process_immediately
            )
            responses.append(result)
        except HTTPException as e:
            # Add error response for this document and continue with others
            responses.append({
                "document_id": None,
                "message": e.detail,
                "status": "failed"
            })
        except Exception as e:
            # Add error response for this document and continue with others
            responses.append({
                "document_id": None,
                "message": f"Error processing document: {str(e)}",
                "status": "failed"
            })
    
    return responses


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


@router.post("/documents/upload-multiple", response_model=List[DocumentUploadResponse])
async def upload_multiple_documents(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...),
    process_immediately: bool = Query(True, description="Start processing immediately after upload")
):
    """
    Upload multiple documents for processing simultaneously.
    
    Args:
        files: A list of document files to upload
        process_immediately: Whether to start processing immediately
        
    Returns:
        List of DocumentUploadResponse with document IDs and statuses
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files provided for upload"
        )
    
    responses = []
    
    for file in files:
        # Handle each file using the existing upload_document function logic
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Validate supported file types
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt', '.csv', '.xlsx', '.xls']
        if file_extension not in supported_extensions:
            # Add error response for this file and continue with others
            responses.append({
                "document_id": None,
                "message": f"Unsupported file type: {file_extension}. Supported types: {', '.join(supported_extensions)}",
                "status": "failed"
            })
            continue
        
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save the file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            # Add error response for this file and continue with others
            responses.append({
                "document_id": None,
                "message": f"Error saving file: {str(e)}",
                "status": "failed"
            })
            continue
        
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
        
        # Add success response for this file
        responses.append(DocumentUploadResponse(
            document_id=document.id,
            message=f"Document {filename} uploaded successfully",
            status=document.status
        ))
    
    return responses 