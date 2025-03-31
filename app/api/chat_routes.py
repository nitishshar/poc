import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Body, Depends, HTTPException,
                     Path, Query, WebSocket, WebSocketDisconnect)
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.chat_service import ChatMessage, chat_service
from app.services.document_processor import get_document

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
    document_ids: List[str] = Field(default_factory=list)
    messages: List[ChatMessageModel] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    chat_mode: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class ChatMessageRequest(BaseModel):
    """Pydantic model for chat message requests."""
    text: str


class ChatSessionRequest(BaseModel):
    """Pydantic model for chat session creation requests."""
    name: Optional[str] = None
    document_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    chat_mode: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class DocumentUpdateRequest(BaseModel):
    """Request model for adding or removing a document from a chat session."""
    document_id: str


@router.get("/sessions", response_model=List[ChatSessionModel])
async def get_chat_sessions():
    """Get all chat sessions."""
    sessions = chat_service.get_sessions()
    return [ChatSessionModel(**session.to_dict()) for session in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionModel)
async def get_chat_session(session_id: str = Path(..., description="The ID of the chat session")):
    """Get a chat session by ID."""
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    return ChatSessionModel(**session.to_dict())


@router.post("/sessions", response_model=ChatSessionModel)
async def create_chat_session(request: ChatSessionRequest = Body(...)):
    """Create a new chat session."""
    session = chat_service.create_session(
        name=request.name,
        document_id=request.document_id,
        document_ids=request.document_ids,
        chat_mode=request.chat_mode,
        llm_provider=request.llm_provider,
        llm_model=request.llm_model
    )
    return ChatSessionModel(**session.to_dict())


@router.delete("/sessions/{session_id}", response_model=Dict[str, Any])
async def delete_chat_session(session_id: str = Path(..., description="The ID of the chat session")):
    """Delete a chat session."""
    success = chat_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    return {"success": True, "message": f"Chat session with ID {session_id} deleted"}


@router.delete("/sessions", response_model=Dict[str, Any])
async def reset_all_chat_sessions():
    """Reset all chat sessions. Use with caution!
    This is primarily for recovery from corrupted session data."""
    success = chat_service.clear_all_sessions()
    if success:
        return {"success": True, "message": "All chat sessions have been reset"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reset chat sessions")


@router.post("/sessions/{session_id}/documents", response_model=ChatSessionModel)
async def add_document_to_session(
    session_id: str = Path(..., description="The ID of the chat session"),
    request: DocumentUpdateRequest = Body(...)
):
    """Add a document to a chat session."""
    # Validate document exists
    document = get_document(request.document_id)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {request.document_id} not found")
    
    # Check if multi-document chat is enabled
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    if len(session.document_ids) >= settings.MAX_DOCUMENTS_PER_CHAT and not settings.ENABLE_MULTI_DOCUMENT_CHAT:
        raise HTTPException(
            status_code=400, 
            detail=f"Multi-document chat is disabled or maximum documents per chat ({settings.MAX_DOCUMENTS_PER_CHAT}) reached"
        )
    
    # Add document to session
    updated_session = chat_service.add_document_to_session(session_id, request.document_id)
    if not updated_session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    return ChatSessionModel(**updated_session.to_dict())


@router.delete("/sessions/{session_id}/documents/{document_id}", response_model=ChatSessionModel)
async def remove_document_from_session(
    session_id: str = Path(..., description="The ID of the chat session"),
    document_id: str = Path(..., description="The ID of the document to remove")
):
    """Remove a document from a chat session."""
    updated_session = chat_service.remove_document_from_session(session_id, document_id)
    if not updated_session:
        raise HTTPException(status_code=404, detail=f"Chat session with ID {session_id} not found")
    
    return ChatSessionModel(**updated_session.to_dict())


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


# Add WebSocket endpoint for real-time chat
@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """Real-time chat via WebSocket."""
    await websocket.accept()
    
    try:
        # Validate session exists
        session = chat_service.get_session(session_id)
        if not session:
            await websocket.send_json({
                "error": f"Chat session with ID {session_id} not found",
                "status": "error"
            })
            await websocket.close()
            return
            
        # Send initial session data
        await websocket.send_json({
            "type": "session_data",
            "data": session.to_dict()
        })
        
        # Listen for messages
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            
            try:
                # Parse received data
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                context_window = message_data.get("context_window", 5)
                
                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "error": "No message provided",
                        "status": "error"
                    })
                    continue
                
                # Send acknowledgment that message was received
                await websocket.send_json({
                    "type": "status",
                    "status": "processing",
                    "message": "Processing your message..."
                })
                
                # Add user message to the session
                user_chat_message = ChatMessage(text=user_message, role="user")
                session.add_message(user_chat_message)
                
                # Send user message confirmation
                await websocket.send_json({
                    "type": "message",
                    "message": user_chat_message.to_dict(),
                    "status": "received"
                })
                
                # Generate response asynchronously
                updated_session = await chat_service.generate_response(
                    session_id, 
                    user_message,
                    context_window
                )
                
                if updated_session and updated_session.messages:
                    # Get the latest assistant message
                    latest_message = updated_session.messages[-1]
                    
                    # Send the assistant's response
                    await websocket.send_json({
                        "type": "message",
                        "message": latest_message.to_dict(),
                        "status": "complete"
                    })
                    
                    # Send updated session data
                    await websocket.send_json({
                        "type": "session_data",
                        "data": updated_session.to_dict()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Failed to generate response",
                        "status": "error"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON format",
                    "status": "error"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Error processing message: {str(e)}",
                    "status": "error"
                })
                
    except WebSocketDisconnect:
        print(f"WebSocket client disconnected from session {session_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": f"Server error: {str(e)}",
                "status": "error"
            })
        except:
            pass 