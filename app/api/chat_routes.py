from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Path, Body
from pydantic import BaseModel, Field
from uuid import UUID

from app.services.chat_service import chat_service, ChatMessage
from app.services.document_processor import get_document
from app.config.settings import settings

router = APIRouter(prefix=f"{settings.API_V1_STR}/chat")


class ChatMessageModel(BaseModel):
    """Pydantic model for chat messages."""
    id: Optional[str] = None
    text: str
    role: str = "user"
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ChatSessionModel(BaseModel):
    """Pydantic model for chat sessions."""
    id: Optional[str] = None
    name: Optional[str] = None
    document_id: Optional[str] = None
    messages: List[ChatMessageModel] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    text: str


class ChatSessionCreateRequest(BaseModel):
    """Request model for creating a chat session."""
    name: Optional[str] = None
    document_id: Optional[str] = None


@router.post("/sessions", response_model=ChatSessionModel)
async def create_chat_session(
    request: ChatSessionCreateRequest = Body(...)
):
    """Create a new chat session."""
    # Validate document_id if provided
    if request.document_id:
        document = get_document(request.document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document with ID {request.document_id} not found")
    
    # Create a session
    session = chat_service.create_session(
        document_id=request.document_id,
        name=request.name
    )
    
    return ChatSessionModel(**session.to_dict())


@router.get("/sessions", response_model=List[ChatSessionModel])
async def get_chat_sessions():
    """Get all chat sessions."""
    sessions = chat_service.get_all_sessions()
    return [ChatSessionModel(**session.to_dict()) for session in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionModel)
async def get_chat_session(session_id: str = Path(..., description="The ID of the chat session")):
    """Get a chat session by ID."""
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    return ChatSessionModel(**session.to_dict())


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str = Path(..., description="The ID of the chat session")):
    """Delete a chat session."""
    success = chat_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    return {"message": f"Chat session {session_id} deleted successfully"}


@router.post("/sessions/{session_id}/messages", response_model=ChatSessionModel)
async def send_message(
    session_id: str = Path(..., description="The ID of the chat session"),
    request: ChatMessageRequest = Body(...),
    context_window: int = Query(5, description="Number of previous messages to include as context")
):
    """Send a message to a chat session and get a response."""
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    # Generate a response (this also adds the user message to the session)
    await chat_service.generate_response(session_id, request.text, context_window)
    
    # Return the updated session
    return ChatSessionModel(**session.to_dict())


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageModel])
async def get_messages(
    session_id: str = Path(..., description="The ID of the chat session"),
    limit: int = Query(50, description="Maximum number of messages to return")
):
    """Get messages from a chat session."""
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    messages = session.get_messages()
    if limit and limit < len(messages):
        messages = messages[-limit:]
    
    return [ChatMessageModel(**message.to_dict()) for message in messages] 