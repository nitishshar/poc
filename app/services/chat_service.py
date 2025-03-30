import asyncio
import logging
import os
import pickle
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

import anthropic  # For Claude
# Import LLM providers (new)
import openai
from google.generativeai import GenerativeModel  # For Gemini

from app.config.settings import settings
from app.models.document import DocumentModel
from app.services.document_processor import get_document
from app.services.embedding import query_embeddings

logger = logging.getLogger(__name__)

# Path for storing chat sessions
CHAT_SESSIONS_PATH = os.path.join(settings.UPLOAD_DIR, "chat_sessions.pkl")

# LLM Provider base class (new)
class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
    
    async def generate_completion(self, 
                                 prompt: str, 
                                 context: str, 
                                 history: List[Dict[str, str]],
                                 **kwargs) -> str:
        """Generate a completion from the LLM."""
        raise NotImplementedError("Subclasses must implement this method")


# OpenAI Provider implementation (new)
class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = kwargs.get("model", "gpt-3.5-turbo")
        
    async def generate_completion(self, 
                                 prompt: str, 
                                 context: str, 
                                 history: List[Dict[str, str]],
                                 **kwargs) -> str:
        """Generate a completion using OpenAI API."""
        try:
            # Format messages for OpenAI ChatCompletion
            messages = []
            
            # System message with context
            system_content = "You are a helpful assistant that answers questions based on the provided context."
            if context:
                system_content += f"\n\nContext information:\n{context}"
            
            messages.append({"role": "system", "content": system_content})
            
            # Add conversation history
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["text"]})
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1000)
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.exception(f"Error generating OpenAI completion: {str(e)}")
            return f"I encountered an error while generating a response: {str(e)}"


# Gemini Provider implementation (new)
class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        import google.generativeai as genai
        genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        self.model_name = kwargs.get("model", "gemini-pro")
        self.model = GenerativeModel(self.model_name)
        
    async def generate_completion(self, 
                                 prompt: str, 
                                 context: str, 
                                 history: List[Dict[str, str]],
                                 **kwargs) -> str:
        """Generate a completion using Google Gemini API."""
        try:
            # Format conversation for Gemini
            chat = self.model.start_chat(history=[])
            
            # Add context as system message if available
            if context:
                system_message = f"Context information:\n{context}\n\nPlease answer based on this context."
                chat.send_message(system_message, role="user")
            
            # Add conversation history
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                chat.send_message(msg["text"], role=role)
                
            # Get response to the current prompt
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            logger.exception(f"Error generating Gemini completion: {str(e)}")
            return f"I encountered an error while generating a response: {str(e)}"


# Anthropic Claude Provider implementation (new)
class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = kwargs.get("model", "claude-3-sonnet-20240229")
        
    async def generate_completion(self, 
                                 prompt: str, 
                                 context: str, 
                                 history: List[Dict[str, str]],
                                 **kwargs) -> str:
        """Generate a completion using Anthropic Claude API."""
        try:
            # Format messages for Claude
            messages = []
            
            # Add context as system message if available
            system_content = "You are a helpful assistant that answers questions based on the provided context."
            if context:
                system_content += f"\n\nContext information:\n{context}"
            
            # Add conversation history
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["text"]})
            
            # Generate response
            response = self.client.messages.create(
                model=self.model,
                system=system_content,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=kwargs.get("temperature", 0.7)
            )
            
            return response.content[0].text
        except Exception as e:
            logger.exception(f"Error generating Claude completion: {str(e)}")
            return f"I encountered an error while generating a response: {str(e)}"


# LLM Factory to get the appropriate provider (new)
class LLMFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def get_provider(provider_name: str, **kwargs) -> LLMProvider:
        """Get the appropriate LLM provider."""
        providers = {
            "openai": OpenAIProvider,
            "gemini": GeminiProvider,
            "claude": ClaudeProvider
        }
        
        provider_class = providers.get(provider_name.lower())
        if not provider_class:
            logger.warning(f"Provider {provider_name} not found, falling back to OpenAI")
            provider_class = OpenAIProvider
            
        return provider_class(**kwargs)

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
        chat_mode: Optional[str] = None,
        llm_provider: Optional[str] = None,  # New: LLM provider name
        llm_model: Optional[str] = None  # New: Specific model to use
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
        
        # New attributes for flexible LLM selection
        self.llm_provider = llm_provider or settings.DEFAULT_LLM_PROVIDER
        self.llm_model = llm_model or settings.DEFAULT_LLM_MODEL
    
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
            "chat_mode": self.chat_mode,
            "llm_provider": self.llm_provider,  # New field
            "llm_model": self.llm_model  # New field
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
            chat_mode=data.get("chat_mode", settings.CHAT_MODE),
            llm_provider=data.get("llm_provider", settings.DEFAULT_LLM_PROVIDER),  # New field
            llm_model=data.get("llm_model", settings.DEFAULT_LLM_MODEL)  # New field
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
        chat_mode: Optional[str] = None,
        llm_provider: Optional[str] = None,  # New parameter
        llm_model: Optional[str] = None  # New parameter
    ) -> ChatSession:
        """Create a new chat session."""
        # Default to the settings value if not provided
        chat_mode = chat_mode or settings.CHAT_MODE
        llm_provider = llm_provider or settings.DEFAULT_LLM_PROVIDER
        llm_model = llm_model or settings.DEFAULT_LLM_MODEL
        
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
            chat_mode=chat_mode,
            llm_provider=llm_provider,
            llm_model=llm_model
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
        relevant_sections = []
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
                    
            except Exception as e:
                logger.exception(f"Error retrieving relevant sections: {str(e)}")
                relevant_sections = []
        
        # Create concatenated context from relevant sections
        context_text = ""
        if relevant_sections:
            context_text = "Here are the most relevant sections from the documents:\n\n" + "\n\n".join(relevant_sections)
        
        # Format previous conversation into a list of messages
        history = [msg.to_dict() for msg in recent_messages]
        
        try:
            # Get the appropriate LLM provider based on session settings
            provider = LLMFactory.get_provider(
                provider_name=session.llm_provider,
                model=session.llm_model,
                api_key=None  # Use environment variable
            )
            
            # Generate response using the provider
            response_text = await provider.generate_completion(
                prompt=message_text,
                context=context_text,
                history=history,
                temperature=0.7,
                max_tokens=1000
            )
            
            # If response is empty, generate a fallback response
            if not response_text:
                response_text = "I couldn't generate a response. Please try rephrasing your question."
                
        except Exception as e:
            logger.exception(f"Error generating response: {str(e)}")
            response_text = (
                f"I'm sorry, I encountered an error while processing your question: {str(e)}. "
                f"Please try again or ask a different question."
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