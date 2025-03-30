from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class DocumentStatus(str, Enum):
    """Enumeration of possible document processing statuses."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ProcessingStep(str, Enum):
    """Enumeration of processing steps."""
    TEXT_EXTRACTION = "text_extraction"
    OCR = "ocr"
    TABLE_DETECTION = "table_detection"
    TEXT_CHUNKING = "text_chunking"
    EMBEDDING_GENERATION = "embedding_generation"
    METADATA_EXTRACTION = "metadata_extraction"
    COMPLETED = "completed"


class StepStatus(str, Enum):
    """Enumeration of step statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessingStepInfo(BaseModel):
    """Information about a processing step."""
    step: ProcessingStep
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0
    message: Optional[str] = None
    error: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Metadata extracted from a document."""
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    content_type: Optional[str] = None
    custom_metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class TableInfo(BaseModel):
    """Information about a detected table."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    page_number: int
    rows: int
    columns: int
    coordinates: Dict[str, float]  # x1, y1, x2, y2 in PDF coordinates
    caption: Optional[str] = None
    header: Optional[List[str]] = None
    data: List[List[str]] = Field(default_factory=list)
    

class TextChunk(BaseModel):
    """A chunk of text from a document."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None
    section_title: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # x1, y1, x2, y2 in PDF coordinates


class DocumentModel(BaseModel):
    """Document model for storage and retrieval."""
    id: UUID = Field(default_factory=uuid4)
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    upload_time: datetime = Field(default_factory=datetime.now)
    status: DocumentStatus = DocumentStatus.UPLOADED
    processing_steps: List[ProcessingStepInfo] = Field(default_factory=list)
    metadata: Optional[DocumentMetadata] = None
    text_chunks: List[TextChunk] = Field(default_factory=list)
    tables: List[TableInfo] = Field(default_factory=list)
    embedding_collection_name: Optional[str] = None
    error_message: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }


class DocumentResponse(BaseModel):
    """Response model for document information."""
    id: UUID
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    upload_time: datetime
    status: DocumentStatus
    metadata: Optional[DocumentMetadata] = None
    processing_progress: float  # 0 to 1
    current_step: Optional[ProcessingStep] = None
    error_message: Optional[str] = None
    

class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    document_id: UUID
    message: str
    status: DocumentStatus


class DocumentUploadRequest(BaseModel):
    """Request for document upload by path or URL."""
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    process_immediately: bool = True
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_path": "C:/path/to/document.pdf",
                    "process_immediately": True
                },
                {
                    "file_url": "https://example.com/document.pdf",
                    "process_immediately": True
                }
            ]
        }
    } 