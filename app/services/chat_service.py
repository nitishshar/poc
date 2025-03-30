import asyncio
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
import logging
from uuid import UUID

from app.services.embedding import query_embeddings
from app.services.document_processor import get_document
from app.models.document import DocumentModel

logger = logging.getLogger(__name__)

class ChatMessage:
    """Represents a chat message in a conversation."""
    
    def __init__(self, 
                text: str, 
                role: str = "user", 
                timestamp: Optional[datetime] = None,
                id: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.role = role  # "user" or "assistant"
        self.timestamp = timestamp or datetime.now()
        self.id = id or str(uuid.uuid4())
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create a message from a dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            text=data["text"],
            role=data["role"],
            timestamp=timestamp,
            id=data.get("id"),
            metadata=data.get("metadata", {})
        )


class ChatSession:
    """Represents a chat session with message history."""
    
    def __init__(
        self,
        id: Optional[str] = None,
        name: Optional[str] = None,
        document_id: Optional[UUID] = None,
        messages: Optional[List[ChatMessage]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name or f"Chat {self.id[:8]}"
        self.document_id = document_id
        self.messages = messages or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the chat history."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get messages from the chat history."""
        if limit is not None:
            return self.messages[-limit:]
        return self.messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "document_id": str(self.document_id) if self.document_id else None,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create a session from a dictionary."""
        document_id = data.get("document_id")
        if document_id:
            document_id = UUID(document_id)
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            document_id=document_id,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at
        )


class ChatService:
    """Service for managing chat sessions and generating responses."""
    
    def __init__(self):
        """Initialize the chat service."""
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(
        self, 
        name: Optional[str] = None, 
        document_id: Optional[UUID] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(name=name, document_id=document_id)
        self.sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> List[ChatSession]:
        """Get all chat sessions."""
        return list(self.sessions.values())
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def add_message(self, session_id: str, message: ChatMessage) -> Optional[ChatSession]:
        """Add a message to a chat session."""
        session = self.get_session(session_id)
        if session:
            session.add_message(message)
            return session
        return None
    
    async def generate_response(
        self, 
        session_id: str, 
        message_text: str,
        context_window: int = 5
    ) -> Optional[ChatSession]:
        """
        Generate a response to a message using document embeddings.
        
        Args:
            session_id: The ID of the chat session
            message_text: The text of the user's message
            context_window: Number of recent messages to include for context
            
        Returns:
            Updated chat session with the response added
        """
        # Get the chat session
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Chat session {session_id} not found")
            return None
        
        # Add the user message
        user_message = ChatMessage(text=message_text, role="user")
        session.add_message(user_message)
        
        # Check if we have an associated document
        document = None
        if session.document_id:
            document = get_document(session.document_id)
            if not document:
                logger.error(f"Document {session.document_id} not found for chat session {session_id}")
        
        # Get recent chat history for context
        recent_messages = session.get_messages(context_window)
        context = "\n".join([f"{m.role}: {m.text}" for m in recent_messages[:-1]]) if len(recent_messages) > 1 else ""
        
        # Construct a query for embeddings
        query = message_text
        if context:
            query = f"Context: {context}\nQuestion: {message_text}"
        
        # Response text and metadata
        response_text = ""
        response_metadata = {}
        
        # Generate response based on document embeddings if available
        if document and document.embedding_collection_name:
            try:
                # Query embeddings
                results = await query_embeddings(
                    collection_name=document.embedding_collection_name,
                    query_text=query,
                    n_results=3
                )
                
                if results:
                    # Format embedding results
                    response_metadata["results"] = results
                    
                    # Extract the most relevant chunks
                    relevant_sections = []
                    for idx, result in enumerate(results):
                        text = result.get("text", "").strip()
                        relevance = 1 - result.get("distance", 0)
                        metadata = result.get("metadata", {})
                        
                        # Format source information
                        source_info = []
                        if metadata.get("page_number"):
                            source_info.append(f"Page {metadata['page_number']}")
                        if metadata.get("section_title"):
                            source_info.append(f"Section: {metadata['section_title']}")
                            
                        source_str = f" (Source: {', '.join(source_info)})" if source_info else ""
                        
                        relevant_sections.append(f"[Relevance: {relevance:.2f}{source_str}]\n{text}")
                    
                    # Combine results into a coherent response
                    all_text = "\n\n".join(relevant_sections)
                    
                    # Format a user-friendly response
                    response_text = (
                        f"Based on your document, I found the following information:\n\n"
                        f"{all_text}\n\n"
                        f"This information comes from '{document.original_filename}'. "
                        f"Is there anything specific you'd like to know more about?"
                    )
                else:
                    response_text = (
                        f"I couldn't find any relevant information about '{message_text}' "
                        f"in the document '{document.original_filename}'. "
                        f"Could you try rephrasing your question or asking about a different topic?"
                    )
            except Exception as e:
                logger.exception(f"Error generating response: {str(e)}")
                response_text = (
                    f"I'm sorry, I encountered an error while processing your question. "
                    f"Please try again or ask a different question."
                )
        else:
            # Generate a generic response for sessions without documents
            response_text = (
                f"I don't have a document to reference for this chat session. "
                f"Please upload a document and link it to this chat, or ask me a general question."
            )
        
        # Add the assistant's response
        assistant_message = ChatMessage(
            text=response_text,
            role="assistant",
            metadata=response_metadata
        )
        session.add_message(assistant_message)
        
        return session


# Create a singleton instance
chat_service = ChatService() 