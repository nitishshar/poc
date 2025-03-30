import asyncio
import logging
import os
import pickle
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

from app.config.settings import settings
from app.models.document import DocumentModel
from app.services.document_processor import get_document
from app.services.embedding import query_embeddings

logger = logging.getLogger(__name__)

# Path for storing chat sessions
CHAT_SESSIONS_PATH = os.path.join(settings.UPLOAD_DIR, "chat_sessions.pkl")

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
        document_ids: Optional[List[UUID]] = None,
        messages: Optional[List[ChatMessage]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        chat_mode: Optional[str] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name or f"Chat {self.id[:8]}"
        
        # Support both single document_id (for backward compatibility) and multiple document_ids
        self.document_id = document_id  # For backward compatibility
        self.document_ids = document_ids or []
        
        # If document_id is provided but document_ids is empty, add it to document_ids
        if document_id and not document_ids:
            self.document_ids = [document_id]
            
        self.messages = messages or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.chat_mode = chat_mode or settings.CHAT_MODE
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the chat history."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get messages from the chat history."""
        if limit is not None:
            return self.messages[-limit:]
        return self.messages
    
    def add_document(self, document_id: UUID) -> None:
        """Add a document to the chat session."""
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)
            # Update document_id for backward compatibility
            if not self.document_id:
                self.document_id = document_id
            self.updated_at = datetime.now()
    
    def remove_document(self, document_id: UUID) -> bool:
        """Remove a document from the chat session."""
        if document_id in self.document_ids:
            self.document_ids.remove(document_id)
            # Update document_id for backward compatibility
            if self.document_id == document_id:
                self.document_id = self.document_ids[0] if self.document_ids else None
            self.updated_at = datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "document_id": str(self.document_id) if self.document_id else None,
            "document_ids": [str(doc_id) for doc_id in self.document_ids] if self.document_ids else [],
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "chat_mode": self.chat_mode
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """Create a session from a dictionary."""
        document_id = data.get("document_id")
        if document_id:
            document_id = UUID(document_id)
        
        document_ids = data.get("document_ids", [])
        if document_ids:
            document_ids = [UUID(doc_id) for doc_id in document_ids]
        
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
            document_ids=document_ids,
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            chat_mode=data.get("chat_mode", settings.CHAT_MODE)
        )


class ChatService:
    """Service for managing chat sessions and generating responses."""
    
    def __init__(self):
        """Initialize the chat service."""
        self.sessions: Dict[str, ChatSession] = {}
        
        # Only load sessions if persistence is enabled
        if settings.PERSIST_CHAT_SESSIONS:
            self._load_sessions()
    
    def _load_sessions(self):
        """Load chat sessions from disk."""
        try:
            if os.path.exists(CHAT_SESSIONS_PATH):
                with open(CHAT_SESSIONS_PATH, 'rb') as f:
                    loaded_sessions = pickle.load(f)
                    if isinstance(loaded_sessions, dict):
                        self.sessions = loaded_sessions
                        logger.info(f"Loaded {len(self.sessions)} chat sessions from {CHAT_SESSIONS_PATH}")
                    else:
                        logger.error(f"Invalid chat sessions format in {CHAT_SESSIONS_PATH}")
        except Exception as e:
            logger.error(f"Error loading chat sessions: {str(e)}")
            # Ensure the directory exists
            os.makedirs(os.path.dirname(CHAT_SESSIONS_PATH), exist_ok=True)
    
    def _save_sessions(self):
        """Save chat sessions to disk."""
        # Skip saving if persistence is disabled
        if not settings.PERSIST_CHAT_SESSIONS:
            return
            
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(CHAT_SESSIONS_PATH), exist_ok=True)
            
            with open(CHAT_SESSIONS_PATH, 'wb') as f:
                pickle.dump(self.sessions, f)
        except Exception as e:
            logger.error(f"Error saving chat sessions: {str(e)}")
    
    def create_session(
        self, 
        name: Optional[str] = None, 
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        chat_mode: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session."""
        # Default to the settings value if not provided
        chat_mode = chat_mode or settings.CHAT_MODE
        
        # Convert string document_id to UUID if provided
        doc_id_uuid = None
        if document_id:
            try:
                doc_id_uuid = UUID(document_id)
            except ValueError:
                logger.error(f"Invalid document ID format: {document_id}")
        
        # Convert string document_ids to UUID if provided
        doc_ids_uuid = []
        if document_ids:
            for doc_id in document_ids:
                try:
                    doc_ids_uuid.append(UUID(doc_id))
                except ValueError:
                    logger.error(f"Invalid document ID format: {doc_id}")
        
        # If we have a document_id but no document_ids, add it to document_ids
        if doc_id_uuid and not doc_ids_uuid:
            doc_ids_uuid = [doc_id_uuid]
            
        # Create the session with the document IDs
        session = ChatSession(
            name=name, 
            document_id=doc_id_uuid, 
            document_ids=doc_ids_uuid,
            chat_mode=chat_mode
        )
        
        self.sessions[session.id] = session
        self._save_sessions()
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
            self._save_sessions()
            return True
        return False
    
    def add_message(self, session_id: str, message: ChatMessage) -> Optional[ChatSession]:
        """Add a message to a chat session."""
        session = self.get_session(session_id)
        if session:
            session.add_message(message)
            self._save_sessions()
            return session
        return None
    
    def add_document_to_session(self, session_id: str, document_id: str) -> Optional[ChatSession]:
        """Add a document to a chat session."""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Chat session {session_id} not found")
            return None
            
        try:
            doc_id_uuid = UUID(document_id)
            session.add_document(doc_id_uuid)
            self._save_sessions()
            return session
        except ValueError:
            logger.error(f"Invalid document ID format: {document_id}")
            return None
    
    def remove_document_from_session(self, session_id: str, document_id: str) -> Optional[ChatSession]:
        """Remove a document from a chat session."""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Chat session {session_id} not found")
            return None
            
        try:
            doc_id_uuid = UUID(document_id)
            if session.remove_document(doc_id_uuid):
                self._save_sessions()
            return session
        except ValueError:
            logger.error(f"Invalid document ID format: {document_id}")
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
        
        # Check for documents in the session
        documents = []
        if session.document_ids:
            for doc_id in session.document_ids:
                doc = get_document(doc_id)
                if doc:
                    documents.append(doc)
                else:
                    logger.warning(f"Document {doc_id} not found for chat session {session_id}")
        
        # If no documents found via document_ids but we have a legacy document_id, try that
        if not documents and session.document_id:
            doc = get_document(session.document_id)
            if doc:
                documents.append(doc)
        
        # Generate response based on document embeddings if available
        if documents:
            try:
                all_results = []
                
                # Query embeddings for each document
                for document in documents:
                    if document.embedding_collection_name:
                        results = await query_embeddings(
                            collection_name=document.embedding_collection_name,
                            query_text=query,
                            n_results=3
                        )
                        
                        if results:
                            # Add document information to results
                            for result in results:
                                result["document_title"] = document.original_filename
                                result["document_id"] = str(document.id)
                            
                            all_results.extend(results)
                
                # Sort all results by relevance
                all_results.sort(key=lambda x: x.get("distance", 1.0))
                
                # Take the top results across all documents
                top_results = all_results[:min(len(all_results), 5)]
                
                if top_results:
                    # Format embedding results
                    response_metadata["results"] = top_results
                    
                    # Extract the most relevant chunks
                    relevant_sections = []
                    for idx, result in enumerate(top_results):
                        text = result.get("text", "").strip()
                        relevance = 1 - result.get("distance", 0)
                        metadata = result.get("metadata", {})
                        document_title = result.get("document_title", "Unknown")
                        
                        # Format source information
                        source_info = [f"Document: {document_title}"]
                        if metadata.get("page_number"):
                            source_info.append(f"Page {metadata['page_number']}")
                        if metadata.get("section_title"):
                            source_info.append(f"Section: {metadata['section_title']}")
                            
                        source_str = f" (Source: {', '.join(source_info)})"
                        
                        relevant_sections.append(f"[Relevance: {relevance:.2f}{source_str}]\n{text}")
                    
                    # Combine results into a coherent response
                    all_text = "\n\n".join(relevant_sections)
                    
                    # Get document titles for the response
                    doc_titles = [doc.original_filename for doc in documents]
                    
                    # Format a user-friendly response
                    if len(documents) == 1:
                        doc_info = f"document '{doc_titles[0]}'"
                    else:
                        if len(doc_titles) == 2:
                            doc_info = f"documents '{doc_titles[0]}' and '{doc_titles[1]}'"
                        else:
                            # Format document titles with quotes and join them
                            quoted_titles = ["'" + title + "'" for title in doc_titles[:-1]]
                            doc_info = f"documents {', '.join(quoted_titles)}, and '{doc_titles[-1]}'"
                    
                    # Choose response format based on chat mode
                    if session.chat_mode == "assistant":
                        # More conversational assistant-style response
                        response_text = (
                            f"Based on the {doc_info}, here's what I found:\n\n"
                            f"{all_text}\n\n"
                            f"Is there anything specific you'd like me to explain further?"
                        )
                    else:
                        # More raw, completion-style response with sources shown
                        response_text = (
                            f"Based on your query, I found the following information in the {doc_info}:\n\n"
                            f"{all_text}\n\n"
                            f"Is there anything specific you'd like to know more about?"
                        )
                else:
                    doc_titles = [doc.original_filename for doc in documents]
                    if len(documents) == 1:
                        doc_info = f"document '{doc_titles[0]}'"
                    else:
                        if len(doc_titles) == 2:
                            doc_info = f"documents '{doc_titles[0]}' and '{doc_titles[1]}'"
                        else:
                            # Format document titles with quotes and join them
                            quoted_titles = ["'" + title + "'" for title in doc_titles[:-1]]
                            doc_info = f"documents {', '.join(quoted_titles)}, and '{doc_titles[-1]}'"
                    
                    response_text = (
                        f"I couldn't find any relevant information about '{message_text}' "
                        f"in the {doc_info}. "
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
                f"I don't have any documents to reference for this chat session. "
                f"Please add one or more documents to the chat, or ask me a general question."
            )
        
        # Create and add the assistant's response
        response_message = ChatMessage(
            text=response_text,
            role="assistant",
            metadata=response_metadata
        )
        session.add_message(response_message)
        
        # Save the updated session
        self._save_sessions()
        
        return session


# Create a singleton instance
chat_service = ChatService() 