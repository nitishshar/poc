import os
import time
from functools import wraps
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from cachetools import TTLCache

from app.frontend.config import (
    API_BASE_URL,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    API_TIMEOUT,
    CACHE_MAX_ENTRIES,
    CACHE_TTL,
)
from app.frontend.utils import retry_with_backoff


def cached(ttl: int = CACHE_TTL, maxsize: int = CACHE_MAX_ENTRIES):
    """Decorator for caching function results with TTL."""
    cache = TTLCache(maxsize=maxsize, ttl=ttl)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get result from cache
            if cache_key in cache:
                return cache[cache_key]
            
            # If not in cache, call function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = result
            return result
        return wrapper
    return decorator


class APIClient:
    """Handles all API interactions with caching and retry logic."""
    
    @staticmethod
    def join_url(path: str) -> str:
        """Join API base URL with path."""
        return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    
    @staticmethod
    @cached(ttl=CACHE_TTL, maxsize=1)
    def check_health() -> bool:
        """Check API health with caching."""
        try:
            response = requests.get(
                APIClient.join_url("health"),
                timeout=API_TIMEOUT
            )
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    @cached(ttl=CACHE_TTL, maxsize=CACHE_MAX_ENTRIES)
    @retry_with_backoff(max_retries=API_MAX_RETRIES, initial_delay=API_RETRY_DELAY)
    def get_chat_sessions() -> List[Dict[str, Any]]:
        """Get all chat sessions with caching and retry logic."""
        response = requests.get(
            APIClient.join_url("chat/sessions"),
            timeout=API_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        st.error(f"Failed to get chat sessions: {response.status_code}")
        return []
    
    @staticmethod
    @cached(ttl=CACHE_TTL, maxsize=CACHE_MAX_ENTRIES)
    def get_chat_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chat session with caching."""
        try:
            response = requests.get(
                APIClient.join_url(f"chat/sessions/{session_id}"),
                timeout=API_TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                st.error("Chat session not found.")
            else:
                st.error(f"Failed to get chat session: {response.status_code}")
            return None
        except Exception as e:
            st.error(f"Error getting chat session: {str(e)}")
            return None
    
    @staticmethod
    @retry_with_backoff(max_retries=API_MAX_RETRIES, initial_delay=API_RETRY_DELAY)
    def create_chat_session(**kwargs) -> Optional[Dict[str, Any]]:
        """Create a new chat session."""
        try:
            response = requests.post(
                APIClient.join_url("chat/sessions"),
                json=kwargs,
                timeout=API_TIMEOUT
            )
            if response.status_code == 201:
                # Clear relevant caches
                APIClient.get_chat_sessions.cache_clear()
                return response.json()
            else:
                st.error(f"Failed to create chat session: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Error creating chat session: {str(e)}")
            return None
    
    @staticmethod
    @retry_with_backoff(max_retries=API_MAX_RETRIES, initial_delay=API_RETRY_DELAY)
    def delete_chat_session(session_id: str) -> bool:
        """Delete a chat session."""
        try:
            # Use the exact path from the backend API
            # From chat_routes.py: @router.delete("/sessions/{session_id}")
            exact_endpoint = f"{API_BASE_URL.rstrip('/')}/chat/sessions/{session_id}"
            print(f"DEBUG: Attempting to delete session {session_id} using endpoint: {exact_endpoint}")
            
            response = requests.delete(
                exact_endpoint,
                timeout=API_TIMEOUT
            )
            
            # Log detailed response for debugging
            print(f"DEBUG: Delete response status code: {response.status_code}")
            print(f"DEBUG: Delete response content: {response.text}")
            
            if response.status_code in (200, 204):
                # Clear relevant caches
                try:
                    APIClient.get_chat_sessions.cache_clear()
                except:
                    pass
                try:
                    APIClient.get_chat_session.cache_clear()
                except:
                    pass
                return True
            else:
                st.error(f"Failed to delete chat session: {response.status_code}")
                return False
        except Exception as e:
            st.error(f"Error deleting chat session: {str(e)}")
            return False
    
    @staticmethod
    @retry_with_backoff(max_retries=API_MAX_RETRIES, initial_delay=API_RETRY_DELAY)
    def rename_chat_session(session_id: str, new_name: str) -> bool:
        """Rename a chat session."""
        try:
            # Try first endpoint (chat/sessions/{id})
            response = requests.patch(
                APIClient.join_url(f"chat/sessions/{session_id}"),
                json={"name": new_name},
                timeout=API_TIMEOUT
            )
            
            # If 404, try alternative endpoint (chats/{id})
            if response.status_code == 404:
                alt_response = requests.patch(
                    APIClient.join_url(f"chat/{session_id}"),
                    json={"name": new_name},
                    timeout=API_TIMEOUT
                )
                
                # If that fails too, try another format (chats/{id})
                if alt_response.status_code == 404:
                    final_response = requests.patch(
                        APIClient.join_url(f"chats/{session_id}"),
                        json={"name": new_name},
                        timeout=API_TIMEOUT
                    )
                    if final_response.status_code in (200, 204):
                        # Clear relevant caches
                        APIClient.get_chat_sessions.cache_clear()
                        APIClient.get_chat_session.cache_clear()
                        return True
                
                if alt_response.status_code in (200, 204):
                    # Clear relevant caches
                    APIClient.get_chat_sessions.cache_clear()
                    APIClient.get_chat_session.cache_clear()
                    return True
            
            if response.status_code in (200, 204):
                # Clear relevant caches
                APIClient.get_chat_sessions.cache_clear()
                APIClient.get_chat_session.cache_clear()
                return True
                
            return False
        except Exception as e:
            st.error(f"Error renaming chat session: {str(e)}")
            return False
    
    @staticmethod
    @retry_with_backoff(max_retries=API_MAX_RETRIES, initial_delay=API_RETRY_DELAY)
    def send_message(session_id: str, message: str, context_window: int = 5) -> Optional[Dict[str, Any]]:
        """Send a message to a chat session."""
        try:
            response = requests.post(
                APIClient.join_url(f"chat/sessions/{session_id}/messages"),
                json={"text": message, "context_window": context_window},
                timeout=API_TIMEOUT * 2  # Double timeout for message sending
            )
            if response.status_code == 200:
                # Clear session cache
                APIClient.get_chat_session.cache_clear()
                return response.json()
            else:
                st.error(f"Failed to send message: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Error sending message: {str(e)}")
            return None
    
    @staticmethod
    @st.cache_data(ttl=300)
    def get_documents() -> List[Dict[str, Any]]:
        """Get all documents with caching."""
        try:
            # Add include_metadata=true parameter to get complete document details
            response = requests.get(
                APIClient.join_url("documents"),
                params={"include_metadata": "true", "include_processing_info": "true"},
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching documents: {str(e)}")
            return []
    
    @staticmethod
    def upload_document(file_name: str, file_content: bytes, content_type: str = None) -> Dict[str, Any]:
        """Upload a document file to the API."""
        try:
            files = {
                'file': (file_name, file_content, content_type)
            }
            
            response = requests.post(
                APIClient.join_url("documents/upload"),
                files=files,
                timeout=API_TIMEOUT * 2  # Longer timeout for uploads
            )
            
            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def import_document_from_url(url: str) -> Dict[str, Any]:
        """Import a document from a URL."""
        try:
            # Use the upload-by-path endpoint which accepts URLs as per backend code
            response = requests.post(
                APIClient.join_url("documents/upload"),
                data={"file_url": url, "process_immediately": "true"},
                timeout=API_TIMEOUT * 2  # Longer timeout for imports
            )
            
            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def import_document_from_path(path: str) -> Dict[str, Any]:
        """Import a document from a server path."""
        try:
            # Use the upload endpoint with file_path parameter
            response = requests.post(
                APIClient.join_url("documents/upload"),
                data={"file_path": path, "process_immediately": "true"},
                timeout=API_TIMEOUT * 2  # Longer timeout for imports
            )
            
            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def delete_document(document_id: str) -> Dict[str, Any]:
        """Delete a document from the system."""
        try:
            response = requests.delete(
                APIClient.join_url(f"documents/{document_id}"),
                timeout=API_TIMEOUT
            )
            
            if response.status_code in (200, 204):
                return {"success": True, "message": "Document deleted successfully"}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def reprocess_document(document_id: str) -> Dict[str, Any]:
        """Reprocess a document."""
        try:
            response = requests.post(
                APIClient.join_url(f"documents/{document_id}/reprocess"),
                timeout=API_TIMEOUT
            )
            
            if response.status_code in (200, 202):
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_document_status(document_id: str) -> Dict[str, Any]:
        """Get the current status of a document."""
        try:
            response = requests.get(
                APIClient.join_url(f"documents/{document_id}/status"),
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def semantic_search(query: str, doc_ids: List[str] = None, top_k: int = 10, threshold: float = 0.7) -> Dict[str, Any]:
        """Perform semantic search on document embeddings."""
        try:
            payload = {
                "query": query,
                "top_k": top_k,
                "threshold": threshold
            }
            
            # Add document IDs if specified
            if doc_ids:
                payload["document_ids"] = doc_ids
                
            # The correct search endpoint path
            response = requests.post(
                APIClient.join_url("documents/search"),
                json=payload,
                timeout=API_TIMEOUT * 2  # Longer timeout for search
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def generate_embeddings(document_id: str) -> Dict[str, Any]:
        """Generate embeddings for a document."""
        try:
            response = requests.post(
                APIClient.join_url(f"documents/{document_id}/embeddings"),
                timeout=API_TIMEOUT * 3  # Even longer timeout for embedding generation
            )
            
            if response.status_code in (200, 202):
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"API error: {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)} 