import asyncio
import base64
import enum
import io
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import websockets
from PIL import Image

from app.config.settings import settings

# Initialize session state variables
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = []

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
    
if "current_session_cache" not in st.session_state:
    st.session_state.current_session_cache = None
    
if "show_new_chat_form" not in st.session_state:
    st.session_state.show_new_chat_form = False

# WebSocket connection state
if "ws_connection" not in st.session_state:
    st.session_state.ws_connection = None
    
if "ws_messages" not in st.session_state:
    st.session_state.ws_messages = {}

# Available LLM providers and models
LLM_PROVIDERS = {
    "openai": {
        "display_name": "OpenAI",
        "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    },
    "gemini": {
        "display_name": "Google Gemini",
        "models": ["gemini-pro", "gemini-1.5-pro"]
    },
    "claude": {
        "display_name": "Anthropic Claude",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    }
}

# Create a ResponseType enum here to avoid import issues
class ResponseType(Enum):
    """Enumeration of possible response types for visualization."""
    TEXT = auto()         # Plain text responses
    TABLE = auto()        # Table-like content
    CHART = auto()        # Chart/graph content
    IMAGE = auto()        # Image content/references
    FILE = auto()         # File download references
    LIST = auto()         # List-formatted content
    ERROR = auto()        # Error messages
    METADATA = auto()     # Document metadata
    MULTI = auto()        # Multiple content types combined

# Create a simplified ResponseAnalyzer class here
class ResponseAnalyzer:
    """
    Analyze text responses to determine the best visualization method.
    """
    
    def __init__(self):
        # Chart-related keywords that might suggest data suitable for charts
        self.chart_keywords = [
            "graph", "chart", "plot", "trend", "distribution", "histogram", 
            "bar chart", "pie chart", "line graph", "scatter plot", "time series",
            "comparison", "percentage", "statistics", "visualization", "diagram",
            "proportion", "frequency", "count"
        ]
        
        # Keywords that might indicate table data
        self.table_keywords = [
            "table", "grid", "row", "column", "cell", "header", "value",
            "tabular", "matrix", "csv", "spreadsheet", "data frame", "dataset",
            "data set", "entries", "records", "fields"
        ]
        
        # Pattern for list items
        self.list_pattern = r"(\n\s*[-*•]\s+[^\n]+){3,}"
        self.numbered_list_pattern = r"(\n\s*\d+\.\s+[^\n]+){3,}"
        
        # Markdown table patterns
        self.markdown_table_pattern = r"\|[^|]+\|[^|]+\|"
        self.markdown_table_separator = r"\|[\s*:?\-+]+\|"

    def analyze(self, query: str, response: str) -> Dict[str, Any]:
        """
        Simplified analysis that detects the type of response.
        """
        result = {
            "response_type": ResponseType.TEXT,  # Default to TEXT
            "visualization_type": None,
            "visualization_data": None,
            "confidence": 1.0
        }
        
        # Check for tables
        if "|" in response and "-+-" in response or "---" in response:
            result["response_type"] = ResponseType.TABLE
            # Extract table data if needed
        
        # Check for lists
        elif re.search(r"(\n\s*[-*•]\s+.+){3,}", response) or re.search(r"(\n\s*\d+\.\s+.+){3,}", response):
            result["response_type"] = ResponseType.LIST
            # Extract list items if present
            items = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line.startswith('- ') or line.startswith('* ') or line.startswith('• ')):
                    items.append(line[2:].strip())
                elif line and re.match(r'^\d+\.', line):
                    items.append(re.sub(r'^\d+\.\s+', '', line))
            if items:
                result["visualization_data"] = items
        
        # Check for potential chart data
        elif any(kw in query.lower() for kw in ["chart", "graph", "plot", "distribution"]):
            # Very simple check for chart data patterns
            result["response_type"] = ResponseType.CHART
            result["visualization_type"] = "bar"  # Default
            
            # Determine chart type from query
            if "pie" in query.lower():
                result["visualization_type"] = "pie"
            elif "line" in query.lower() or "trend" in query.lower():
                result["visualization_type"] = "line"
        
        return result

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")

# Ensure proper URL joining that preserves the /api path
def join_api_url(base_url, path):
    """Join API base URL with path, ensuring the /api part is preserved.
    This handles the case where urllib.parse.urljoin might remove the /api path."""
    # If the base URL doesn't end with a slash, and path starts with a slash,
    # urljoin might discard the last path component of base_url
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    return urljoin(base_url, path.lstrip('/'))

# Initialize ResponseAnalyzer
response_analyzer = ResponseAnalyzer()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def format_datetime(dt_str):
    """Format datetime string to human-readable format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_chat_sessions():
    """Get all chat sessions from the API."""
    # Create a placeholder for displaying status
    api_error_container = None
    
    # Add retry logic for server errors
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            url = join_api_url(API_BASE_URL, "/chat/sessions")
            print(f"Fetching chat sessions from: {url} (attempt {attempt}/{max_retries})")
            
            response = requests.get(url, timeout=5)
            
            # Handle server errors with retries
            if response.status_code == 500:
                error_msg = f"Server error (attempt {attempt}/{max_retries}): {response.text[:200]}..."
                print(error_msg)
                
                # Check if it's the specific AttributeError we're seeing
                if "AttributeError: 'ChatService' object has no attribute 'get_sessions'" in response.text:
                    error_message = ("Backend error: The chat service is missing the get_sessions method. "
                                    "This is likely a backend code issue that needs to be fixed.")
                    print(error_message)
                    try:
                        st.error(error_message)
                    except:
                        # If we're not in a Streamlit context, ignore the UI error
                        pass
                    # Return empty list instead of retrying - this won't be fixed with retries
                    return []
                    
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Increase the delay for next retry (exponential backoff)
                    retry_delay *= 2
                    continue
            
            # Handle other non-200 status codes
            if response.status_code != 200:
                print(f"Non-200 response: {response.status_code} - {response.text[:200]}...")
                
                if attempt < max_retries and response.status_code >= 500:
                    # Only retry for server errors (5xx)
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                # If we reached here, we've either exhausted retries or got a non-retryable error
                error_message = f"Error fetching chat sessions: {response.status_code} {response.reason}"
                if response.status_code == 500:
                    error_message += " - The server encountered an internal error. This might be temporary or require backend maintenance."
                    
                    # Add more specific advice for the AttributeError
                    if "AttributeError: 'ChatService' object has no attribute 'get_sessions'" in response.text:
                        error_message += "\n\nSpecific error: The chat service is missing the get_sessions method. This is a backend code issue."
                        
                elif response.status_code == 404:
                    error_message += " - The chat sessions endpoint was not found. Check API configuration."
                elif response.status_code == 401 or response.status_code == 403:
                    error_message += " - Authentication or authorization issue. Check your credentials."
                
                # Show error in the UI - safely
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                
                # Return an empty list to avoid breaking the UI
                return []
            
            # Success! Parse and return the data
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout:
            error_msg = f"Request timed out on attempt {attempt}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = "Error fetching chat sessions: Request timed out. The server might be under heavy load or unreachable."
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return []
                
        except requests.ConnectionError:
            error_msg = f"Connection error on attempt {attempt}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = "Error fetching chat sessions: Connection failed. Please check if the API server is running."
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return []
                
        except Exception as e:
            error_msg = f"Unexpected error on attempt {attempt}: {str(e)}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = f"Error fetching chat sessions: {str(e)}"
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                import traceback
                print(traceback.format_exc())
                return []
    
    # If we reach here, all retries failed
    error_message = "Failed to fetch chat sessions after multiple attempts. Please check server logs for details."
    print(error_message)
    try:
        st.error(error_message)
    except:
        # If we're not in a Streamlit context, ignore the UI error
        pass
    return []

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_chat_session(session_id):
    """Get a chat session by ID."""
    # Add retry logic for server errors
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            # Ensure ID is properly formatted as UUID
            formatted_id = format_uuid_if_needed(session_id)
            if formatted_id != session_id:
                print(f"Reformatted session ID from {session_id} to {formatted_id}")
                
            # Try with the formatted ID
            url = join_api_url(API_BASE_URL, f"/chat/sessions/{formatted_id}")
            print(f"Getting chat session from: {url} (attempt {attempt}/{max_retries})")
            
            response = requests.get(url, timeout=5)
            
            # Handle server errors with retries
            if response.status_code == 500:
                error_msg = f"Server error (attempt {attempt}/{max_retries}): {response.text[:200]}..."
                print(error_msg)
                
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Increase the delay for next retry (exponential backoff)
                    retry_delay *= 2
                    continue
            
            # Log detailed response info for debugging
            print(f"Response status: {response.status_code}, Content: {response.text[:100]}...")
            
            # Handle non-200 responses
            if response.status_code != 200:
                # Try fallback with original ID only if it's a 404 (maybe formatting is the issue)
                if response.status_code == 404 and formatted_id != session_id:
                    backup_url = join_api_url(API_BASE_URL, f"/chat/sessions/{session_id}")
                    print(f"Got 404, trying fallback URL: {backup_url}")
                    backup_response = requests.get(backup_url, timeout=5)
                    
                    if backup_response.status_code == 200:
                        print("Fallback request succeeded")
                        return backup_response.json()
                    else:
                        print(f"Fallback also failed: {backup_response.status_code}")
                
                # For other server errors, retry
                if attempt < max_retries and response.status_code >= 500:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                # If we've exhausted retries or got a non-retryable error
                error_message = f"Error fetching chat session: {response.status_code} {response.reason}"
                if response.status_code == 500:
                    error_message += " - The server encountered an internal error. This might be temporary or require backend maintenance."
                elif response.status_code == 404:
                    error_message += f" - Chat session with ID {session_id} not found."
                elif response.status_code == 401 or response.status_code == 403:
                    error_message += " - Authentication or authorization issue. Check your credentials."
                
                # Show error in the UI - safely
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                
                # Return None to indicate failure
                return None
            
            # Success path
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout:
            error_msg = f"Request timed out on attempt {attempt}/{max_retries}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = "Error fetching chat session: Request timed out. The server might be under heavy load or unreachable."
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return None
                
        except requests.ConnectionError:
            error_msg = f"Connection error on attempt {attempt}/{max_retries}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = "Error fetching chat session: Connection failed. Please check if the API server is running."
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return None
                
        except Exception as e:
            error_msg = f"Unexpected error on attempt {attempt}/{max_retries}: {str(e)}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = f"Error fetching chat session: {str(e)}"
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                import traceback
                print(traceback.format_exc())
                return None
    
    # If we reach here, all retries failed
    error_message = "Failed to fetch chat session after multiple attempts. Please check server logs for details."
    print(error_message)
    try:
        st.error(error_message)
    except:
        # If we're not in a Streamlit context, ignore the UI error
        pass
    return None

def create_chat_session(document_id=None, document_ids=None, name=None, chat_mode="completion", llm_provider=None, llm_model=None):
    """Create a new chat session."""
    try:
        payload = {}
        if document_id:
            payload["document_id"] = document_id
        if document_ids:
            payload["document_ids"] = document_ids
        if name:
            payload["name"] = name
        if chat_mode:
            payload["chat_mode"] = chat_mode
        if llm_provider:
            payload["llm_provider"] = llm_provider
        if llm_model:
            payload["llm_model"] = llm_model
        
        # Log the request for debugging
        print(f"Creating chat session with payload: {payload}")
        
        # Construct the API URL
        url = join_api_url(API_BASE_URL, "/chat/sessions")
        print(f"Sending request to: {url}")
        
        # Send the request with detailed logging
        print(f"Request headers: {{'Content-Type': 'application/json'}}")
        print(f"Request body: {json.dumps(payload)}")
        
        response = requests.post(
            url,
            json=payload,
            timeout=10  # Add a timeout to avoid hanging indefinitely
        )
        
        # Log response details
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response content: {response.text[:500]}...")
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            # Clear the chat sessions cache to force refresh
            get_chat_sessions.clear()
            get_chat_session.clear()
            return result
        else:
            error_msg = f"Failed to create chat session. Server returned: {response.status_code} - {response.text}"
            st.error(error_msg)
            print(error_msg)
            
            # Try to check if we can access the API at all
            try:
                test_response = requests.get(join_api_url(API_BASE_URL, "/chat/sessions"), timeout=5)
                print(f"Test API connection status: {test_response.status_code}")
                if test_response.status_code != 200:
                    print("API connection test failed - cannot access chat sessions endpoint")
            except Exception as conn_err:
                print(f"API connection test error: {str(conn_err)}")
            
            return None
    except Exception as e:
        error_msg = f"Exception creating chat session: {str(e)}"
        st.error(error_msg)
        print(error_msg)
        return None

def delete_chat_session(session_id):
    """Delete a chat session."""
    try:
        # Ensure ID is properly formatted
        formatted_id = format_uuid_if_needed(session_id)
        response = requests.delete(join_api_url(API_BASE_URL, f"/chat/sessions/{formatted_id}"))
        response.raise_for_status()
        # Clear the chat sessions cache to force refresh
        get_chat_sessions.clear()
        return True
    except Exception as e:
        st.error(f"Error deleting chat session: {str(e)}")
        return False

def send_message(session_id, message, context_window=5):
    """Send a message to a chat session."""
    try:
        # Ensure ID is properly formatted
        formatted_id = format_uuid_if_needed(session_id)
        url = join_api_url(API_BASE_URL, f"/chat/sessions/{formatted_id}/messages")
        print(f"Sending message to: {url}")
        print(f"Message content: {message[:50]}{'...' if len(message) > 50 else ''}")
        print(f"Context window: {context_window}")
        
        # Add retry logic for 500 errors
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    url,
                    params={"context_window": context_window},
                    json={"text": message},
                    timeout=30  # Increase timeout for complex messages
                )
                
                print(f"Send message response status: {response.status_code}")
                
                if response.status_code == 500:
                    error_msg = f"Server error (attempt {attempt}/{max_retries}): {response.text[:200]}..."
                    print(error_msg)
                    
                    if attempt < max_retries:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        # Double the delay for next retry (exponential backoff)
                        retry_delay *= 2
                        continue
                    else:
                        # If all retries fail, show error to user
                        st.error(f"Failed to send message after {max_retries} attempts. Server returned a 500 error.")
                        print(f"Full error response: {response.text}")
                        return None
                        
                if response.status_code != 200:
                    print(f"Error response content: {response.text[:200]}...")
                    
                # Only raise for status if not a 500 (since we handle 500s separately)
                if response.status_code != 500:
                    response.raise_for_status()
                    
                # If we reach here, the request was successful
                # Clear the session cache to get the updated session
                get_chat_session.clear()
                return response.json()
                
            except requests.Timeout:
                print(f"Request timed out on attempt {attempt}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    st.error(f"Request timed out after {max_retries} attempts.")
                    return None
            except requests.RequestException as req_err:
                print(f"Request error on attempt {attempt}: {str(req_err)}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    st.error(f"Network error: {str(req_err)}")
                    return None
                
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        print(f"Exception in send_message: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_documents():
    """Get all documents from the API with retry logic for server errors."""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            url = join_api_url(API_BASE_URL, "/documents")
            print(f"Getting documents from: {url} (attempt {attempt}/{max_retries})")
            
            response = requests.get(url, timeout=10)
            
            # Handle different response status codes
            if response.status_code != 200:
                error_message = f"Error fetching documents: {response.status_code} {response.reason}"
                
                # More specific error messages based on status code
                if response.status_code == 500:
                    error_message += " - Server error. This might be temporary."
                elif response.status_code == 401 or response.status_code == 403:
                    error_message += " - Authentication or authorization issue."
                
                # For server errors, retry
                if response.status_code >= 500 and attempt < max_retries:
                    print(f"Server error on attempt {attempt}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                # If we've exhausted retries or got a non-retryable error
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return []
            
            documents = response.json()
            print(f"Successfully fetched {len(documents)} documents")
            return documents
            
        except requests.Timeout:
            error_msg = f"Request timed out on attempt {attempt}/{max_retries}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = "Error fetching documents: Request timed out. The server might be under heavy load."
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return []
                
        except requests.ConnectionError:
            error_msg = f"Connection error on attempt {attempt}/{max_retries}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = "Error fetching documents: Connection failed. Please check if the API server is running."
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                return []
                
        except Exception as e:
            error_msg = f"Unexpected error on attempt {attempt}/{max_retries}: {str(e)}"
            print(error_msg)
            
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                error_message = f"Error fetching documents: {str(e)}"
                print(error_message)
                try:
                    st.error(error_message)
                except:
                    # If we're not in a Streamlit context, ignore the UI error
                    pass
                import traceback
                print(traceback.format_exc())
                return []
    
    # If we reach here, all retries failed
    error_message = "Failed to fetch documents after multiple attempts. Please check server logs for details."
    print(error_message)
    try:
        st.error(error_message)
    except:
        # If we're not in a Streamlit context, ignore the UI error
        pass
    return []

@st.cache_data
def visualize_response(query, response_text, metadata=None):
    """
    Visualize the response based on its content type.
    Analyzes the response and renders appropriate visualization.
    
    Args:
        query: The original query
        response_text: The text response
        metadata: Optional metadata from the response
    """
    # Analyze the response to determine visualization type
    analysis = response_analyzer.analyze(query, response_text)
    
    if metadata and "results" in metadata:
        # This is a special case for embedding search results
        visualize_search_results(metadata["results"])
        return
    
    response_type = analysis["response_type"]
    
    if response_type == ResponseType.TEXT:
        # No special visualization needed, just display the text
        st.markdown(response_text)
    
    elif response_type == ResponseType.TABLE:
        # Try to extract and display a table
        try:
            # Convert visualization data to DataFrame if not already
            data = analysis["visualization_data"]
            if isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, dict) and "headers" in data and "data" in data:
                df = pd.DataFrame(data["data"], columns=data["headers"])
            elif isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = None
                
            if df is not None and not df.empty:
                st.markdown("**Extracted Table:**")
                st.dataframe(df)
                
                # Also show the original text for context
                with st.expander("Show original text"):
                    st.markdown(response_text)
            else:
                st.markdown(response_text)
                
        except Exception as e:
            st.warning(f"Could not parse table data: {str(e)}")
            st.markdown(response_text)
    
    elif response_type == ResponseType.CHART:
        # Try to render a chart if the text suggests chart data
        chart_type = analysis["visualization_type"]
        try:
            data = analysis["visualization_data"]
            
            if isinstance(data, dict) and "labels" in data and "values" in data:
                # Simple chart data
                labels = data["labels"]
                values = data["values"]
                
                if chart_type == "bar":
                    fig = px.bar(x=labels, y=values, labels={"x": "Category", "y": "Value"})
                    st.plotly_chart(fig, use_container_width=True)
                elif chart_type == "line":
                    fig = px.line(x=labels, y=values, labels={"x": "Category", "y": "Value"})
                    st.plotly_chart(fig, use_container_width=True)
                elif chart_type == "pie":
                    fig = px.pie(values=values, names=labels)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                # We couldn't extract chart data, show the text response
                st.markdown(response_text)
                
        except Exception as e:
            st.warning(f"Could not generate chart: {str(e)}")
            st.markdown(response_text)
        
    elif response_type == ResponseType.LIST:
        # Display list items in a streamlit container
        try:
            data = analysis["visualization_data"]
            if isinstance(data, list):
                for item in data:
                    st.markdown(f"- {item}")
            else:
                st.markdown(response_text)
        except Exception:
            st.markdown(response_text)
    
    else:
        # For other types, just display the text
        st.markdown(response_text)

@st.cache_data
def visualize_search_results(results):
    """
    Visualize search results from document embeddings.
    
    Args:
        results: List of search results
    """
    if not results:
        st.info("No search results found.")
        return
    
    st.markdown("### Search Results")
    
    # Show relevance scores in a chart
    scores = [1 - result.get("distance", 0) for result in results]
    labels = [f"Result {i+1}" for i in range(len(results))]
    
    fig = px.bar(
        x=labels, 
        y=scores, 
        labels={"x": "Result", "y": "Relevance Score"},
        title="Result Relevance"
    )
    fig.update_layout(
        yaxis=dict(range=[0, 1])
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Display individual results
    for i, result in enumerate(results):
        with st.expander(f"Result {i+1} - Relevance: {scores[i]:.4f}"):
            text = result.get("text", "").strip()
            st.markdown(text)
            
            # Show metadata if available
            metadata = result.get("metadata", {})
            if metadata:
                st.markdown("**Source Information:**")
                meta_text = ""
                
                if metadata.get("page_number"):
                    meta_text += f"- Page: {metadata['page_number']}\n"
                    
                if metadata.get("section_title"):
                    meta_text += f"- Section: {metadata['section_title']}\n"
                    
                if metadata.get("document_title"):
                    meta_text += f"- Document: {metadata['document_title']}\n"
                    
                if metadata.get("is_table"):
                    meta_text += f"- Content Type: Table\n"
                
                st.markdown(meta_text)

@st.cache_data
def is_valid_uuid(val):
    """Check if string is a valid UUID."""
    if not val:  # Handle None or empty string
        return False
        
    try:
        uuid_obj = uuid.UUID(str(val).strip())
        # Make sure the converted UUID string is the same as the input string
        # This ensures the UUID is in the correct format
        return str(uuid_obj) == str(val).strip().lower()
    except (ValueError, AttributeError, TypeError):
        return False

@st.cache_data
def format_uuid_if_needed(val):
    """Format a string to ensure it's a valid UUID string format."""
    if not val:
        return None
        
    try:
        # Convert to UUID and back to string to ensure correct format
        # This ensures consistent casing and formatting
        cleaned_val = str(val).strip().lower().replace('-', '')
        if len(cleaned_val) == 32:  # Valid UUID without dashes
            # Format with dashes in standard UUID format
            return str(uuid.UUID(cleaned_val))
        return str(uuid.UUID(str(val).strip()))
    except (ValueError, AttributeError, TypeError):
        return val  # Return original if not convertible

# WebSocket Helper Functions
def get_ws_url(session_id):
    """Get WebSocket URL for a chat session."""
    # Derive WebSocket URL from API_BASE_URL (replacing http with ws)
    base_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
    return f"{base_url}/chat/ws/{session_id}"

async def connect_websocket(session_id):
    """Connect to WebSocket for a chat session."""
    ws_url = get_ws_url(session_id)
    try:
        connection = await websockets.connect(ws_url)
        # Store session data
        if session_id not in st.session_state.ws_messages:
            st.session_state.ws_messages[session_id] = []
        return connection
    except Exception as e:
        print(f"Error connecting to WebSocket: {str(e)}")
        # Remove the debug check since settings.DEBUG doesn't exist
        # Use an info message which is less intrusive
        st.info("Using standard API instead of real-time connection.")
        return None

async def send_message_ws(websocket, message, context_window=5):
    """Send a message via WebSocket."""
    if not websocket:
        return None
        
    try:
        # Prepare message data
        data = {
            "message": message,
            "context_window": context_window
        }
        
        # Send the message
        await websocket.send(json.dumps(data))
        
        # Wait for and process responses
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                data = json.loads(response)
                
                # Store the message in session state for display
                if data.get("type") == "message" and data.get("status") == "complete":
                    st.session_state.ws_messages[websocket.path.split("/")[-1]].append(data["message"])
                    return data["message"]
                    
                # Update session data if provided
                if data.get("type") == "session_data":
                    st.session_state.current_session_cache = data["data"]
                    
                # Handle errors
                if data.get("type") == "error":
                    st.error(f"Error: {data.get('error')}")
                    return None
                    
            except asyncio.TimeoutError:
                # No message received, continue listening
                await asyncio.sleep(0.1)
                continue
                
    except Exception as e:
        print(f"Error sending message via WebSocket: {str(e)}")
        # Use a warning instead of an error for a less intrusive notification
        st.warning("Real-time connection unavailable. Using standard API instead.")
        return None

def ws_send_message(session_id, message, context_window=5):
    """Send a message using WebSocket or fallback to REST API."""
    # Check if we have websocket support enabled
    if settings.USE_WEBSOCKET_CHAT:
        # Try using WebSocket
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Connect if not connected
            if "ws_connection" not in st.session_state or not st.session_state.ws_connection:
                st.session_state.ws_connection = loop.run_until_complete(connect_websocket(session_id))
            
            # Send message if connected
            if st.session_state.ws_connection:
                result = loop.run_until_complete(send_message_ws(
                    st.session_state.ws_connection, 
                    message, 
                    context_window
                ))
                
                if result:
                    return {"success": True, "message": result}
            
        except Exception as e:
            print(f"WebSocket error: {str(e)}")
            # Remove the debug check since settings.DEBUG doesn't exist
            # No need to show a message here as the connection_websocket function will handle it
            # Close websocket if open
            if "ws_connection" in st.session_state and st.session_state.ws_connection:
                try:
                    loop.run_until_complete(st.session_state.ws_connection.close())
                except:
                    pass
                st.session_state.ws_connection = None
    
    # Fallback to REST API
    response = send_message(session_id, message, context_window)
    
    if response:
        # Get the assistant's response from updated messages
        messages = response.get("messages", [])
        if messages and messages[-1]["role"] == "assistant":
            return {"success": True, "message": messages[-1]}
    
    return {"success": False, "error": "Failed to send message"}

def create_direct_chat_session(key_prefix=""):
    """Creates a new chat session with a simple interface."""
    # Create a placeholder for success message
    status_placeholder = st.empty()
    
    # Get available documents for selection - cache is already applied to get_documents()
    documents = get_documents()
    
    # Check if we have any documents
    if not documents:
        st.warning("No documents available. Please upload documents first.")
        return
    
    # Use form for better performance (reduces reruns)
    with st.form(key=f"{key_prefix}_new_chat_form"):
        # Session name
        session_name = st.text_input(
            "Session Name",
            key=f"{key_prefix}_session_name",
            placeholder="My Chat Session"
        )
        
        # Document selection - multi-select if enabled
        # Create safer document options that handle missing keys
        doc_options = []
        
        # Process documents once and store results
        if "document_options" not in st.session_state:
            st.session_state.document_options = []
        
        # Only rebuild document options if needed
        if not st.session_state.document_options or len(st.session_state.document_options) != len(documents):
            doc_options = []
            for doc in documents:
                doc_id = doc.get("id", "unknown_id")
                
                # Extract title from metadata if available
                metadata = doc.get("metadata", {})
                doc_title = metadata.get("title") if metadata else None
                
                # If no title in metadata, try other possible locations or keys
                if not doc_title:
                    doc_title = doc.get("title", "")  # Try direct title property
                    
                # If still no title, use original_filename or filename
                if not doc_title:
                    doc_title = doc.get("original_filename", "")
                if not doc_title:
                    doc_title = doc.get("filename", "").split('/')[-1] if doc.get("filename") else "Untitled Document"
                
                # Display document info with size or page count
                page_count = None
                if "page_count" in metadata:
                    page_count = metadata.get("page_count")
                elif "pages" in doc:
                    page_count = doc.get("pages")
                    
                if page_count:
                    doc_info = f"{doc_title} ({page_count} pages)"
                elif "file_size" in doc:
                    # Convert bytes to KB/MB if available
                    size_bytes = doc["file_size"]
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} bytes"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                    doc_info = f"{doc_title} ({size_str})"
                else:
                    doc_info = doc_title
                
                doc_options.append((doc_id, doc_info))
                
            # Store in session state to avoid reprocessing
            st.session_state.document_options = doc_options
        else:
            doc_options = st.session_state.document_options
        
        if settings.ENABLE_MULTI_DOCUMENT_CHAT:
            selected_docs = st.multiselect(
                "Select Documents",
                options=[doc[0] for doc in doc_options],
                format_func=lambda x: next((doc[1] for doc in doc_options if doc[0] == x), x),
                key=f"{key_prefix}_multi_docs"
            )
        else:
            selected_doc = st.selectbox(
                "Select Document",
                options=[""] + [doc[0] for doc in doc_options],
                format_func=lambda x: next((doc[1] for doc in doc_options if doc[0] == x), x if x else "None"),
                key=f"{key_prefix}_single_doc"
            )
            selected_docs = [selected_doc] if selected_doc else []
        
        # Model selection
        provider_col, model_col = st.columns(2)
        
        with provider_col:
            provider_options = [(key, info["display_name"]) for key, info in LLM_PROVIDERS.items()]
            selected_provider = st.selectbox(
                "LLM Provider",
                options=[p[0] for p in provider_options],
                format_func=lambda x: next((p[1] for p in provider_options if p[0] == x), x),
                index=[i for i, p in enumerate(provider_options) if p[0] == settings.DEFAULT_LLM_PROVIDER][0] if settings.DEFAULT_LLM_PROVIDER else 0,
                key=f"{key_prefix}_provider"
            )
        
        with model_col:
            # Get models for selected provider
            available_models = LLM_PROVIDERS[selected_provider]["models"] if selected_provider in LLM_PROVIDERS else []
            default_model = settings.DEFAULT_LLM_MODEL if settings.DEFAULT_LLM_MODEL in available_models else (available_models[0] if available_models else "")
            
            selected_model = st.selectbox(
                "LLM Model",
                options=available_models,
                index=available_models.index(default_model) if default_model in available_models else 0,
                key=f"{key_prefix}_model"
            )
        
        # Chat mode
        chat_mode = st.selectbox(
            "Chat Mode",
            options=["completion", "assistant"],
            index=0 if settings.CHAT_MODE == "completion" else 1,
            key=f"{key_prefix}_chat_mode"
        )
        
        # Create session button
        submitted = st.form_submit_button("Create Chat Session", use_container_width=True)
        
        if submitted:
            if not selected_docs:
                status_placeholder.warning("Please select at least one document.")
                return
            
            session_name_to_use = session_name
            
            if not session_name_to_use:
                # Generate a name based on the document title
                if len(selected_docs) == 1:
                    doc_info = next((doc for doc in documents if doc["id"] == selected_docs[0]), None)
                    if doc_info:
                        # Extract title from metadata if available
                        metadata = doc_info.get("metadata", {})
                        doc_title = metadata.get("title") if metadata else None
                        
                        # If no title in metadata, try other possible locations or keys
                        if not doc_title:
                            doc_title = doc_info.get("title", "")  # Try direct title property
                            
                        # If still no title, use original_filename or filename
                        if not doc_title:
                            doc_title = doc_info.get("original_filename", "")
                        if not doc_title:
                            doc_title = doc_info.get("filename", "").split('/')[-1] if doc_info.get("filename") else "Document"
                        
                        session_name_to_use = f"Chat with {doc_title}"
                    else:
                        session_name_to_use = "New Chat Session"
                else:
                    session_name_to_use = f"Multi-document Chat ({len(selected_docs)} docs)"
            
            # Display creating message
            status_placeholder.info("Creating chat session...")
            
            # Create the session
            result = create_chat_session(
                document_ids=selected_docs,
                name=session_name_to_use,
                chat_mode=chat_mode,
                llm_provider=selected_provider,
                llm_model=selected_model
            )
            
            if result:
                # Show success
                status_placeholder.success("Chat session created successfully! You can start chatting now.")
                
                # Set session as current and hide the form
                st.session_state.current_session_id = result["id"]
                st.session_state.newly_created_session = True
                st.session_state.show_new_chat_form = False
                
                # Clear any existing cache for this session
                if "current_session_cache" in st.session_state:
                    del st.session_state.current_session_cache
                
                # Force a rerun to show the chat immediately
                st.rerun()
            else:
                status_placeholder.error("Failed to create chat session. Please try again.")

@st.cache_data(ttl=60)  # Cache for 1 minute
def check_api_health(base_url):
    """Check if the API is healthy - cached to avoid unnecessary requests."""
    try:
        # Get the base URL without the /api path for health check
        health_url = f"{base_url}/health"
        api_check = requests.get(health_url, timeout=2)
        return api_check.status_code == 200
    except Exception:
        return False

def reset_all_chat_sessions():
    """Reset all chat sessions - use with caution!"""
    try:
        url = join_api_url(API_BASE_URL, "/chat/sessions")
        response = requests.delete(url, timeout=5)
        
        if response.status_code == 200:
            # Clear caches
            get_chat_sessions.clear()
            if "current_session_cache" in st.session_state:
                del st.session_state.current_session_cache
            if "chat_sessions" in st.session_state:
                st.session_state.chat_sessions = []
            st.session_state.current_session_id = None
            
            return True, "All chat sessions have been reset successfully."
        else:
            error_message = f"Failed to reset sessions. Server returned: {response.status_code} - {response.text}"
            return False, error_message
    except Exception as e:
        error_message = f"Error resetting chat sessions: {str(e)}"
        return False, error_message

def chat_interface():
    """Streamlit interface for document chat - simplified approach."""
    # Create containers for different parts of the UI to optimize rendering
    title_container = st.container()
    api_status_container = st.empty()
    error_recovery_container = st.empty()
    main_content_container = st.container()
    
    with title_container:
        st.title("Chat with Your Documents")
    
    # API connection check - now using a cached function to improve performance
    # Get the base URL without the /api path for health check
    base_url = API_BASE_URL
    if "/api" in base_url:
        base_url = base_url.split("/api")[0]
        
    api_working = check_api_health(base_url)
    
    # Check for the known ChatService.get_sessions issue
    known_backend_issue = False
    try:
        # Try to fetch sessions but catch any errors
        test_sessions_url = join_api_url(API_BASE_URL, "/chat/sessions")
        test_response = requests.get(test_sessions_url, timeout=3)
        if test_response.status_code == 500 and "AttributeError: 'ChatService' object has no attribute 'get_sessions'" in test_response.text:
            known_backend_issue = True
    except Exception:
        # If we can't even connect, just continue with normal flow
        pass
    
    # Check for the old session format issues
    old_session_format_issue = False
    try:
        # Try to fetch sessions but catch any errors
        test_sessions_url = join_api_url(API_BASE_URL, "/chat/sessions")
        test_response = requests.get(test_sessions_url, timeout=3)
        if test_response.status_code == 500 and "AttributeError: 'ChatSession' object has no attribute 'llm_provider'" in test_response.text:
            old_session_format_issue = True
    except Exception:
        # If we can't even connect, just continue with normal flow
        pass
    
    # Display connection status in a placeholder to avoid full rerenders
    with api_status_container:
        if known_backend_issue:
            st.error("❌ Backend Error: The chat service is missing the get_sessions method.")
            
            # Show detailed error information in the recovery container
            with error_recovery_container:
                st.warning("There is a known issue with the backend chat service implementation.")
                
                solution_tab, debug_tab = st.tabs(["Solution", "Debug Info"])
                
                with solution_tab:
                    st.markdown("""
                    ### Backend Code Issue Detected
                    
                    The error is happening because the ChatService class in the backend doesn't have a method called `get_sessions()` that's being called in `chat_routes.py` on line 62.
                    
                    #### To fix this issue:
                    
                    1. Locate the ChatService class in your backend code
                    2. Add the missing `get_sessions()` method that should return a list of chat sessions
                    3. Restart the backend server
                    
                    #### Example implementation:
                    ```python
                    def get_sessions(self):
                        # Return all chat sessions
                        return self.get_all_sessions()
                    ```
                    
                    Until this is fixed, you can still use the Create New Chat Session feature below,
                    but you won't be able to see or select existing sessions.
                    """)
                    
                    # Allow creating a new session despite the error
                    st.info("You can still create a new chat session:")
                    create_direct_chat_session(key_prefix="error_recovery")
                
                with debug_tab:
                    st.markdown("### Error Details")
                    st.code("""
AttributeError: 'ChatService' object has no attribute 'get_sessions'
File: C:\\poc\\app\\api\\chat_routes.py, Line 62
Error in: get_chat_sessions function

The API endpoint is trying to call:
    sessions = chat_service.get_sessions()
but this method doesn't exist in the ChatService class.
                    """)
                
                # Don't proceed with the rest of the interface
                return
        elif old_session_format_issue:
            st.error("❌ Backend Error: Incompatible session data format.")
            
            # Show detailed error information in the recovery container
            with error_recovery_container:
                st.warning("Your saved chat sessions use an older format that's incompatible with the current version.")
                
                solution_tab, debug_tab, reset_tab = st.tabs(["Solution", "Debug Info", "Reset Sessions"])
                
                with solution_tab:
                    st.markdown("""
                    ### Session Format Issue Detected
                    
                    The error is happening because your saved chat sessions are using an older format 
                    that doesn't include the `llm_provider` and/or `llm_model` fields that are required in the current version.
                    
                    #### To fix this issue, you have two options:
                    
                    1. **Reset all chat sessions** (you'll lose your chat history)
                    2. **Update the backend code** to safely handle older session formats
                    
                    The simplest solution is to reset all sessions using the tab "Reset Sessions".
                    """)
                
                with debug_tab:
                    st.markdown("### Error Details")
                    st.code("""
AttributeError: 'ChatSession' object has no attribute 'llm_provider'
File: C:\\poc\\app\\services\\chat_service.py

The error occurs when trying to access the llm_provider attribute 
that doesn't exist in your older saved chat sessions.
                    """)
                
                with reset_tab:
                    st.warning("⚠️ Warning: Resetting all sessions will delete your chat history. This action cannot be undone.")
                    st.markdown("If you're sure you want to proceed, click the button below:")
                    
                    if st.button("Reset All Chat Sessions", key="reset_sessions_button"):
                        success, message = reset_all_chat_sessions()
                        if success:
                            st.success(message)
                            st.info("Please refresh the page to continue.")
                            # Show a button to refresh
                            if st.button("Refresh Now", key="refresh_after_reset"):
                                st.rerun()
                        else:
                            st.error(message)
                
                # Don't proceed with the rest of the interface
                return
        elif api_working:
            st.success("✅ Connected to API backend")
        else:
            st.error("❌ API health check failed - backend is not responding")
            
            # Show detailed error recovery options in a separate container
            with error_recovery_container:
                st.warning("The application is experiencing connectivity issues with the backend server.")
                
                # Add tabs for different recovery options
                troubleshoot_tab, debug_tab, api_test_tab = st.tabs(["Troubleshooting", "Debug Info", "API Tests"])
                
                with troubleshoot_tab:
                    st.markdown("""
                    ### Troubleshooting Steps:
                    
                    1. **Check if the backend server is running**
                       - Verify that the server process is active
                       - Look for any error messages in the server console
                    
                    2. **Verify API connectivity**
                       - The app is trying to connect to: `{}`
                       - Make sure this URL is correct in your `.env` file
                    
                    3. **Restart the application**
                       - Try stopping and restarting both the frontend and backend
                    
                    4. **Clear browser cache**
                       - Clear your browser cache and refresh the page
                    """.format(API_BASE_URL))
                    
                    if st.button("Retry Connection", key="retry_connection"):
                        # Clear the cache and force a refresh
                        check_api_health.clear()
                        get_chat_sessions.clear()
                        st.rerun()
                
                with debug_tab:
                    st.markdown("### Debug Information")
                    st.code(f"""
API Base URL: {API_BASE_URL}
Health Check URL: {base_url}/health
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    """)
                    
                    # Try to get more specific error details
                    st.markdown("### Recent Error Details")
                    try:
                        error_response = requests.get(join_api_url(API_BASE_URL, "/chat/sessions"), timeout=2)
                        st.code(f"""
Status Code: {error_response.status_code}
Response: 
{error_response.text[:500]}{'...' if len(error_response.text) > 500 else ''}
                        """)
                    except Exception as e:
                        st.code(f"Could not connect to API: {str(e)}")
                
                with api_test_tab:
                    st.markdown("### API Endpoint Tests")
                    st.info("Test specific API endpoints to identify which ones are failing.")
                    
                    # Create columns for different endpoint tests
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Health Check")
                        if st.button("Test Health Endpoint"):
                            try:
                                health_url = f"{base_url}/health"
                                response = requests.get(health_url, timeout=3)
                                if response.status_code == 200:
                                    st.success(f"✅ Health check OK: {response.status_code}")
                                    st.code(response.text[:500])
                                else:
                                    st.error(f"❌ Health check failed: {response.status_code}")
                                    st.code(response.text[:500])
                            except Exception as e:
                                st.error(f"❌ Health check error: {str(e)}")
                        
                        st.markdown("#### Documents API")
                        if st.button("Test Documents Endpoint"):
                            try:
                                doc_url = join_api_url(API_BASE_URL, "/documents")
                                response = requests.get(doc_url, timeout=3)
                                if response.status_code == 200:
                                    st.success(f"✅ Documents API OK: {response.status_code}")
                                    doc_count = len(response.json())
                                    st.info(f"Found {doc_count} documents")
                                else:
                                    st.error(f"❌ Documents API failed: {response.status_code}")
                                    st.code(response.text[:500])
                            except Exception as e:
                                st.error(f"❌ Documents API error: {str(e)}")
                    
                    with col2:
                        st.markdown("#### Chat Sessions API")
                        if st.button("Test Chat Sessions Endpoint"):
                            try:
                                sessions_url = join_api_url(API_BASE_URL, "/chat/sessions")
                                response = requests.get(sessions_url, timeout=3)
                                if response.status_code == 200:
                                    st.success(f"✅ Chat Sessions API OK: {response.status_code}")
                                    session_count = len(response.json())
                                    st.info(f"Found {session_count} chat sessions")
                                else:
                                    st.error(f"❌ Chat Sessions API failed: {response.status_code}")
                                    st.code(response.text[:500])
                            except Exception as e:
                                st.error(f"❌ Chat Sessions API error: {str(e)}")
                        
                        st.markdown("#### Backend Info")
                        if st.button("Test Backend Info Endpoint"):
                            try:
                                # Try a different API endpoint that might work
                                info_url = join_api_url(API_BASE_URL, "/info")
                                response = requests.get(info_url, timeout=3)
                                if response.status_code == 200:
                                    st.success(f"✅ Backend Info API OK: {response.status_code}")
                                    st.code(response.text[:500])
                                else:
                                    st.error(f"❌ Backend Info API failed: {response.status_code}")
                                    st.code(response.text[:500])
                            except Exception as e:
                                st.error(f"❌ Backend Info API error: {str(e)}")
                    
                    # Option to test a custom API endpoint
                    st.markdown("#### Custom API Test")
                    with st.form("custom_api_test"):
                        endpoint = st.text_input("API Endpoint (e.g., /status)", 
                                               value="/status")
                        full_url = join_api_url(API_BASE_URL, endpoint)
                        st.text(f"Full URL: {full_url}")
                        
                        submitted = st.form_submit_button("Test Endpoint")
                        if submitted:
                            try:
                                response = requests.get(full_url, timeout=3)
                                if response.status_code == 200:
                                    st.success(f"✅ API call successful: {response.status_code}")
                                else:
                                    st.error(f"❌ API call failed: {response.status_code}")
                                
                                st.code(f"Response: {response.text[:1000]}")
                            except Exception as e:
                                st.error(f"❌ API call error: {str(e)}")
                
                # Offer to continue in limited functionality mode
                st.markdown("---")
                st.markdown("### Continue in Limited Mode")
                st.info("You can still view the application interface, but some features will be disabled.")
                
                if st.button("Continue in Limited Mode", key="limited_mode"):
                    # Set a session state flag to indicate we're in limited mode
                    st.session_state.limited_mode = True
                    st.success("Entering limited functionality mode...")
                    time.sleep(1)  # Short delay for UX purposes
                
                return
    
    # Check if we're in limited mode
    limited_mode = st.session_state.get("limited_mode", False)
    
    with main_content_container:
        # Initialize session state for chat
        if "chat_sessions" not in st.session_state:
            if api_working or limited_mode:
                # In normal mode, fetch from API; in limited mode, use empty list
                st.session_state.chat_sessions = get_chat_sessions() if api_working else []
            
        if "current_session_id" not in st.session_state:
            # Set default session if available
            if st.session_state.chat_sessions:
                st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
            else:
                st.session_state.current_session_id = None
        
        # If in limited mode, show a persistent indicator
        if limited_mode:
            st.warning("⚠️ Running in limited functionality mode. Some features are disabled.")
            
            # Provide option to exit limited mode
            if st.button("Try to Reconnect", key="exit_limited_mode"):
                st.session_state.limited_mode = False
                check_api_health.clear()
                st.rerun()
        
        # Call the chat page renderer directly
        render_chat_page(limited_mode=limited_mode)

def render_chat_page(limited_mode=False):
    """Render the chat interface page using a simplified approach similar to the example."""
    # Create containers for different parts of the UI to optimize rendering
    header_container = st.container()
    newly_created_container = st.empty()
    
    # Check if we have a newly created session
    newly_created = st.session_state.get("newly_created_session", False)
    
    # Clear the flag to prevent it from triggering again
    if newly_created:
        st.session_state.newly_created_session = False
        with newly_created_container:
            st.success("Chat session created successfully! You can start chatting now.")
    
    with header_container:
        st.header("Chat with Your Documents")
    
    # Cache the current session to avoid repeated API calls
    current_session = None
    if st.session_state.current_session_id and not limited_mode:
        # Format the ID properly before comparison
        formatted_id = format_uuid_if_needed(st.session_state.current_session_id)
        
        # Check if we need to update the cache due to ID formatting changes
        if formatted_id != st.session_state.current_session_id:
            st.session_state.current_session_id = formatted_id
            if "current_session_cache" in st.session_state:
                del st.session_state.current_session_cache
        
        # Now use the cached session or retrieve it
        if "current_session_cache" not in st.session_state or st.session_state.current_session_cache.get("id") != st.session_state.current_session_id:
            current_session = get_chat_session(st.session_state.current_session_id)
            if current_session:
                st.session_state.current_session_cache = current_session
        else:
            current_session = st.session_state.current_session_cache
    
    # Split the page into two columns - session list and chat area
    chat_cols = st.columns([1, 3])
    
    # Left column: Session selection
    with chat_cols[0]:
        sessions_container = st.container()
        with sessions_container:
            st.subheader("Your Chat Sessions")
            
            if not limited_mode:
                # Add a refresh button for sessions
                if st.button("🔄 Refresh Sessions", key="refresh_sessions", use_container_width=True):
                    st.session_state.chat_sessions = get_chat_sessions()
                    if "current_session_cache" in st.session_state:
                        del st.session_state.current_session_cache
                
                # Add a button to create a new session
                if st.button("➕ New Session", key="new_session_button", use_container_width=True):
                    st.session_state.show_new_chat_form = True
            else:
                # In limited mode, these features are disabled
                st.info("Session management is unavailable in limited mode.")
            
            # Show new chat form if requested and not in limited mode
            if st.session_state.get("show_new_chat_form", False) and not limited_mode:
                with st.expander("Create New Session", expanded=True):
                    create_direct_chat_session(key_prefix="sidebar")
                    if st.button("Cancel", key="cancel_new_session"):
                        st.session_state.show_new_chat_form = False
            
            # Create a separate container for session lists to optimize rendering
            session_list_container = st.container()
            with session_list_container:
                # Session selection
                if st.session_state.chat_sessions:
                    st.subheader("Select a Session")
                    
                    # Add a search/filter box for sessions
                    session_filter = st.text_input("Filter sessions", key="session_filter", placeholder="Type to filter...")
                    
                    # Filter and limit displayed sessions
                    filtered_sessions = st.session_state.chat_sessions
                    if session_filter:
                        filtered_sessions = [s for s in st.session_state.chat_sessions 
                                            if session_filter.lower() in s.get("name", "").lower()]
                    
                    # Only show first 10 sessions with a "show more" option if there are more
                    display_limit = 10
                    show_more = len(filtered_sessions) > display_limit
                    
                    if show_more and "session_show_all" not in st.session_state:
                        st.session_state.session_show_all = False
                    
                    if show_more and not st.session_state.get("session_show_all", False):
                        display_sessions = filtered_sessions[:display_limit]
                        st.info(f"Showing {display_limit} of {len(filtered_sessions)} sessions")
                        if st.button("Show all sessions"):
                            st.session_state.session_show_all = True
                    else:
                        display_sessions = filtered_sessions
                    
                    # Create a clean visual selection - use a placeholder for faster updates
                    session_buttons_container = st.container()
                    with session_buttons_container:
                        for session in display_sessions:
                            # Create a clean display name with document info
                            display_name = session["name"]
                            doc_count = len(session.get("document_ids", [])) 
                            if not doc_count and session.get("document_id"):
                                doc_count = 1
                            
                            # Use a cleaner button-like selection
                            session_id = session["id"]
                            is_selected = session_id == st.session_state.current_session_id
                            
                            # Create a highlighted button for the selected session
                            if is_selected:
                                # Display the selected session with a delete button
                                col1, col2 = st.columns([5, 1])
                                with col1:
                                    st.markdown(f"""
                                    <div style="border:1px solid #4CAF50; border-radius:5px; padding:10px; margin:5px 0; background-color:rgba(76, 175, 80, 0.1);">
                                        <strong>{display_name}</strong><br>
                                        <small>{doc_count} document(s)</small>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Only show delete button if not in limited mode
                                if not limited_mode:
                                    with col2:
                                        # Delete button for current session
                                        if st.button("🗑️", key=f"delete_{session_id}", help="Delete this session"):
                                            if delete_chat_session(session_id):
                                                st.success("Session deleted successfully")
                                                # Refresh the session list
                                                st.session_state.chat_sessions = get_chat_sessions()
                                                # Select a new session if available
                                                if st.session_state.chat_sessions:
                                                    st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
                                                else:
                                                    st.session_state.current_session_id = None
                                                if "current_session_cache" in st.session_state:
                                                    del st.session_state.current_session_cache
                            else:
                                # Create a selectable session with a delete button
                                col1, col2 = st.columns([5, 1])
                                with col1:
                                    # Session selection button
                                    if st.button(
                                        f"{display_name} ({doc_count} docs)",
                                        key=f"select_{session_id}",
                                        use_container_width=True
                                    ):
                                        st.session_state.current_session_id = session_id
                                        if "current_session_cache" in st.session_state:
                                            del st.session_state.current_session_cache
                                
                                # Only show delete button if not in limited mode
                                if not limited_mode:
                                    with col2:
                                        # Delete button for this session
                                        if st.button("🗑️", key=f"delete_{session_id}", help="Delete this session"):
                                            if delete_chat_session(session_id):
                                                st.success("Session deleted successfully")
                                                # Refresh the session list
                                                st.session_state.chat_sessions = get_chat_sessions()
                                                # If we deleted the currently selected session, select a new one
                                                if session_id == st.session_state.current_session_id:
                                                    if st.session_state.chat_sessions:
                                                        st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
                                                    else:
                                                        st.session_state.current_session_id = None
                                                    if "current_session_cache" in st.session_state:
                                                        del st.session_state.current_session_cache
                    
                    # Add a button to delete all sessions
                    if not limited_mode:
                        delete_all_container = st.container()
                        with delete_all_container:
                            if st.session_state.chat_sessions:
                                if st.button("🗑️ Delete All Sessions", key="delete_all_sessions"):
                                    # Create a confirmation dialog
                                    if "confirm_delete_all" not in st.session_state:
                                        st.session_state.confirm_delete_all = False
                                        
                                    st.session_state.confirm_delete_all = True
                                    st.warning("Are you sure you want to delete ALL chat sessions? This cannot be undone.")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("Yes, delete all", key="confirm_delete_yes"):
                                            # Delete all sessions
                                            success_count = 0
                                            for session in st.session_state.chat_sessions:
                                                if delete_chat_session(session["id"]):
                                                    success_count += 1
                                            
                                            # Update the UI
                                            st.session_state.chat_sessions = get_chat_sessions()
                                            st.session_state.current_session_id = None
                                            if "current_session_cache" in st.session_state:
                                                del st.session_state.current_session_cache
                                            st.session_state.confirm_delete_all = False
                                            
                                            if success_count > 0:
                                                st.success(f"Successfully deleted {success_count} chat sessions")
                                            else:
                                                st.error("Failed to delete sessions")
                                    with col2:
                                        if st.button("Cancel", key="confirm_delete_no"):
                                            st.session_state.confirm_delete_all = False
                
                elif limited_mode:
                    st.info("Session list is unavailable in limited mode.")
                else:
                    st.info("No chat sessions available. Create a new session to get started.")
    
    # Right column: Chat interface
    with chat_cols[1]:
        chat_interface_container = st.container()
        with chat_interface_container:
            if limited_mode:
                # Show a demo/fallback chat interface in limited mode
                st.warning("Chat functionality is limited without backend connectivity.")
                st.info("You can explore the interface, but messages won't be sent to the server.")
                
                # Display a mock chat interface
                st.header("Chat: Demo Session")
                
                # Display basic mock info
                info_cols = st.columns(3)
                with info_cols[0]:
                    st.markdown("**Model:** OpenAI - gpt-3.5-turbo")
                with info_cols[1]:
                    st.markdown("**Documents:** 1")
                with info_cols[2]:
                    if st.button("🔄 Refresh Chat", key="refresh_current_chat"):
                        st.info("Refresh functionality is disabled in limited mode.")
                
                # Show some mock messages
                with st.chat_message("user"):
                    st.markdown("This is a sample user message.")
                
                with st.chat_message("assistant"):
                    st.markdown("This is a sample AI response. The actual chat functionality requires connection to the backend server.")
                
                # Show mock input
                user_input = st.chat_input("Type your message...", key="chat_input")
                if user_input:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    st.info("Message sending is disabled in limited mode. Please reconnect to the backend server.")
                    
            elif st.session_state.current_session_id and current_session:
                # Regular chat interface when everything is working
                # Get session details
                session_name = current_session.get('name', 'Unnamed Chat')
                chat_mode = current_session.get('chat_mode', settings.CHAT_MODE)
                document_ids = current_session.get('document_ids', [])
                provider = current_session.get('llm_provider', settings.DEFAULT_LLM_PROVIDER)
                model = current_session.get('llm_model', settings.DEFAULT_LLM_MODEL)
                
                if not document_ids and current_session.get('document_id'):
                    document_ids = [current_session['document_id']]
                    
                # Display session header with model info
                st.header(f"Chat: {session_name}")
                
                # Display basic chat info
                info_cols = st.columns(3)
                with info_cols[0]:
                    # Display LLM provider and model
                    provider_display = LLM_PROVIDERS.get(provider, {}).get("display_name", provider)
                    st.markdown(f"**Model:** {provider_display} - {model}")
                with info_cols[1]:
                    st.markdown(f"**Documents:** {len(document_ids)}")
                with info_cols[2]:
                    # Add a refresh button for just this session
                    if st.button("🔄 Refresh Chat", key="refresh_current_chat"):
                        if "current_session_cache" in st.session_state:
                            del st.session_state.current_session_cache
                
                # Only show connection status in special cases
                if settings.USE_WEBSOCKET_CHAT:
                    if "ws_connection" in st.session_state and st.session_state.ws_connection:
                        st.success("⚡ Using real-time connection")
                
                # Display messages using the chat message container for a better look
                messages = current_session.get("messages", [])
                
                # Use a container for better message rendering performance
                message_container = st.container()
                with message_container:
                    # Display all messages
                    for message in messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["text"])
                
                # Chat input - use Streamlit's chat input for better UX
                if user_input := st.chat_input("Type your message...", key="chat_input"):
                    # Add user message to the display immediately
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    
                    # Create a placeholder for any temporary messages
                    response_placeholder = st.empty()
                    
                    # Use a spinner while waiting for response
                    with st.spinner("AI is thinking..."):
                        # Send message with WebSocket or fallback to REST API
                        response = ws_send_message(
                            st.session_state.current_session_id,
                            user_input,
                            context_window=5
                        )
                        
                        if response and response.get("success"):
                            # Clear any temporary messages
                            response_placeholder.empty()
                            
                            # Display the AI response
                            with st.chat_message("assistant"):
                                ai_message = response.get("message", {})
                                response_text = ai_message.get("text", "")
                                if response_text:
                                    st.markdown(response_text)
                                else:
                                    st.warning("Received empty response from AI. Please try again.")
                            
                            # Update session state
                            if "current_session_cache" in st.session_state:
                                # Refresh the session cache
                                current_session = get_chat_session(st.session_state.current_session_id)
                                if current_session:
                                    st.session_state.current_session_cache = current_session
                        else:
                            # Show a friendly error and suggest retry
                            response_placeholder.error("I couldn't process your message at this time. The system may be experiencing temporary issues.")
                            response_placeholder.info("You can try again or check back later.")
                
            elif st.session_state.current_session_id and not current_session and not limited_mode:
                st.error("Error loading chat session. The session may have been deleted.")
                
                # Provide options to recover
                st.info("Options to recover:")
                recovery_col1, recovery_col2 = st.columns([1, 1])
                
                with recovery_col1:
                    if st.button("Try Again", key="try_again_btn"):
                        if "current_session_cache" in st.session_state:
                            del st.session_state.current_session_cache
                
                with recovery_col2:
                    if st.button("Start New Session", key="new_session_btn"):
                        st.session_state.current_session_id = None
                        if "current_session_cache" in st.session_state:
                            del st.session_state.current_session_cache
            else:
                # No current session, show guidance
                st.info("Select a chat session from the list on the left or create a new session to get started.")
                
                # Add a quick direct creation form if not in limited mode
                if not limited_mode:
                    st.markdown("### Create New Chat Session")
                    create_direct_chat_session(key_prefix="main")
                else:
                    st.info("Creating new sessions is unavailable in limited mode.")


if __name__ == "__main__":
    chat_interface() 