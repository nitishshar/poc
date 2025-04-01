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
from app.frontend.api import APIClient
from app.frontend.components import Callbacks, SessionState, UIComponents

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

# --- Session State Initialization ---
def initialize_session_state():
    """Initialize required session state variables if they don't exist."""
    if "containers" not in st.session_state:
        st.session_state.containers = {
            "title": st.container(),
            "status": st.empty(),
            "error_recovery": st.container(),
            "main_area": st.container(),
        }
        print("Initialized UI containers in session state")

    defaults = {
        "current_view": "main",
        "current_session_id": None,
        "chat_sessions": [],
        "current_session_cache": None,
        "newly_created_session": False,
        "sending_message": False,
        "confirm_delete": False,
        "deletion_succeeded": False,
        "api_working": None,
        "backend_issue": None,
        "create_session_key_prefix": "main_create",
        "create_session_success": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- API Status Logic ---
@st.cache_data(ttl=30)
def check_api_health(base_url):
    """Check if the API is healthy - cached."""
    try:
        health_url = f"{base_url}/health"
        api_check = requests.get(health_url, timeout=3)
        return api_check.status_code == 200
    except Exception as e:
        print(f"API Health Check Error: {e}")
        return False

def update_api_status():
    """Check API health and potential backend issues, updating session state."""
    if st.session_state.api_working is None or not st.session_state.api_working:
        base_url = API_BASE_URL
        if "/api" in base_url:
            base_url = base_url.split("/api")[0]
        st.session_state.api_working = check_api_health(base_url)

    if st.session_state.api_working:
        st.session_state.backend_issue = None
        try:
            test_sessions_url = join_api_url(API_BASE_URL, "/chat/sessions")
            test_response = requests.get(test_sessions_url, timeout=5)
            if test_response.status_code == 500:
                if "AttributeError: 'ChatService' object has no attribute 'get_sessions'" in test_response.text:
                    st.session_state.backend_issue = "missing_method"
                elif "AttributeError: 'ChatSession' object has no attribute 'llm_provider'" in test_response.text:
                    st.session_state.backend_issue = "old_format"
        except Exception as e:
            print(f"Error during backend issue check: {e}")
            st.session_state.api_working = False
            st.session_state.backend_issue = "api_offline"
    else:
        st.session_state.backend_issue = "api_offline"
        st.session_state.chat_sessions = []
        st.session_state.current_session_id = None
        st.session_state.current_session_cache = None

def display_status_and_errors(status_container, error_container):
    """Display API status and error recovery UI if needed."""
    with status_container:
        status_container.empty()
        if st.session_state.backend_issue == "missing_method":
            st.error("❌ Backend Error: Chat service code mismatch (missing get_sessions).")
        elif st.session_state.backend_issue == "old_format":
            st.error("❌ Backend Error: Incompatible saved session data format.")
        elif st.session_state.backend_issue == "api_offline":
            st.error("❌ API connection failed. Backend may be offline or unreachable.")
        elif st.session_state.api_working:
            st.success("✅ Connected to API backend")

    if st.session_state.backend_issue:
        with error_container:
            error_container.empty()
            show_error_recovery(st.session_state.backend_issue)
        return False
    else:
        error_container.empty()
        return True

# --- UI Navigation and Callbacks ---
def switch_view(view_name):
    st.session_state.current_view = view_name
    st.session_state.confirm_delete = False

def select_session_callback():
    selected_id = st.session_state.get("session_selector_widget")
    if selected_id and selected_id != st.session_state.current_session_id:
        st.session_state.current_session_id = selected_id
        if "current_session_cache" in st.session_state:
            del st.session_state.current_session_cache
        st.session_state.confirm_delete = False

def refresh_sessions_callback():
    get_chat_sessions.clear()
    st.session_state.chat_sessions = []
    st.toast("Session list refreshed!", icon="🔄")

# --- Deletion Callbacks ---
def handle_delete_session():
    st.session_state.confirm_delete = True

def confirm_delete_session():
    current_session_id = st.session_state.current_session_id
    if not current_session_id: return
    result = delete_chat_session(current_session_id)
    if result:
        st.toast(f"Session deleted successfully!", icon="🗑️")
        st.session_state.deletion_succeeded = True
        st.session_state.current_session_id = None
        if "current_session_cache" in st.session_state: del st.session_state.current_session_cache
        get_chat_sessions.clear()
        st.session_state.chat_sessions = []
    else: st.error("Failed to delete session.")
    st.session_state.confirm_delete = False

def cancel_delete_session():
    st.session_state.confirm_delete = False

# --- Message Sending Callback ---
def handle_send_message():
    user_input = st.session_state.get("chat_input_widget")
    current_session_id = st.session_state.current_session_id
    context_window = st.session_state.get("context_window_widget", 5)
    if not user_input or not current_session_id: return
    with st.spinner("Sending message..."):
        response_data = send_message(current_session_id, user_input, context_window)
        if response_data:
            st.session_state.current_session_cache = response_data
            st.toast("Message sent!", icon="💬")
        else: st.error("Failed to send message.")

def show_error_recovery(issue):
    """Display error recovery UI based on the issue type."""
    if issue == "api_offline":
        st.error("The API backend appears to be offline or unreachable.")
        st.warning("Please check that the backend server is running.")
        if st.button("🔄 Retry Connection", key="retry_connection"):
            st.session_state.api_working = None  # Reset to force re-check
            st.rerun()
    elif issue == "missing_method":
        st.error("The API backend has an incompatible ChatService implementation.")
        st.warning("This could be due to a version mismatch between frontend and backend.")
        st.info("Technical details: The 'get_sessions' method is missing from ChatService.")
        if st.button("🔄 Retry Connection", key="retry_missing_method"):
            st.session_state.api_working = None
            st.rerun()
    elif issue == "old_format":
        st.error("The chat sessions in the database have an incompatible format.")
        st.warning("This could be due to a database schema change between versions.")
        st.info("Technical details: The ChatSession objects are missing 'llm_provider' attribute.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retry Connection", key="retry_old_format"):
                st.session_state.api_working = None
                st.rerun()
        with col2:
            if st.button("⚠️ Reset All Sessions", key="reset_sessions"):
                reset_result, reset_msg = reset_all_chat_sessions()
                if reset_result:
                    st.success(reset_msg)
                    st.session_state.api_working = None
                    st.rerun()
                else:
                    st.error(reset_msg)
    else:
        st.error(f"Unknown backend issue: {issue}")
        if st.button("🔄 Retry Connection", key="retry_unknown"):
            st.session_state.api_working = None
            st.rerun()

# --- API Diagnostic Tab Functions ---
def render_api_diagnostics():
    """Render a diagnostic interface for API endpoints."""
    st.header("API Connection Diagnostics")
    
    # Health check
    st.subheader("Basic API Health")
    base_url = API_BASE_URL
    if "/api" in base_url:
        base_url = base_url.split("/api")[0]
    
    health_col1, health_col2 = st.columns([3, 1])
    with health_col1:
        health_url = f"{base_url}/health"
        st.code(f"GET {health_url}")
    with health_col2:
        if st.button("Test Health", key="test_health"):
            try:
                with st.spinner("Testing API health..."):
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        st.success(f"✅ Health check passed: {response.status_code}")
                        st.json(response.json() if response.text else {})
                    else:
                        st.error(f"❌ Health check failed: {response.status_code}")
                        st.text(response.text[:500])
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
    
    # Sessions endpoint test
    st.subheader("Chat Sessions Endpoint")
    sessions_col1, sessions_col2 = st.columns([3, 1])
    with sessions_col1:
        sessions_url = join_api_url(API_BASE_URL, "/chat/sessions")
        st.code(f"GET {sessions_url}")
    with sessions_col2:
        if st.button("Test Sessions", key="test_sessions"):
            try:
                with st.spinner("Testing sessions endpoint..."):
                    response = requests.get(sessions_url, timeout=5)
                    if response.status_code == 200:
                        st.success(f"✅ Sessions endpoint working: {response.status_code}")
                        data = response.json()
                        st.text(f"Found {len(data)} sessions")
                        if data:
                            st.json(data[0])  # Show first session as example
                    else:
                        st.error(f"❌ Sessions endpoint error: {response.status_code}")
                        st.text(response.text[:500])
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
    
    # Documents endpoint test
    st.subheader("Documents Endpoint")
    docs_col1, docs_col2 = st.columns([3, 1])
    with docs_col1:
        docs_url = join_api_url(API_BASE_URL, "/documents")
        st.code(f"GET {docs_url}")
    with docs_col2:
        if st.button("Test Documents", key="test_docs"):
            try:
                with st.spinner("Testing documents endpoint..."):
                    response = requests.get(docs_url, timeout=5)
                    if response.status_code == 200:
                        st.success(f"✅ Documents endpoint working: {response.status_code}")
                        data = response.json()
                        st.text(f"Found {len(data)} documents")
                        if data:
                            st.json(data[0])  # Show first document as example
                    else:
                        st.error(f"❌ Documents endpoint error: {response.status_code}")
                        st.text(response.text[:500])
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
    
    # Custom endpoint test
    st.subheader("Test Custom Endpoint")
    with st.form("custom_endpoint_form"):
        endpoint = st.text_input("Endpoint Path", value="/chat/sessions", help="Path relative to API base URL")
        method = st.selectbox("HTTP Method", ["GET", "POST", "PUT", "DELETE"])
        timeout = st.slider("Timeout (seconds)", 1, 30, 5)
        test_button = st.form_submit_button("Test Endpoint")
        
    if test_button:
        full_url = join_api_url(API_BASE_URL, endpoint)
        st.code(f"{method} {full_url}")
        try:
            with st.spinner(f"Testing endpoint with {method}..."):
                if method == "GET":
                    response = requests.get(full_url, timeout=timeout)
                elif method == "POST":
                    response = requests.post(full_url, timeout=timeout)
                elif method == "PUT":
                    response = requests.put(full_url, timeout=timeout)
                elif method == "DELETE":
                    response = requests.delete(full_url, timeout=timeout)
                
                st.text(f"Status Code: {response.status_code}")
                try:
                    st.json(response.json())
                except:
                    st.text(response.text[:1000])
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")

@st.cache_data(ttl=30)  # Cache for 5 minutes
def get_documents():
    """Get all documents from the API with robust error handling."""
    print(f"CACHE MISS: get_documents() called at {datetime.now().isoformat()}")
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            url = join_api_url(API_BASE_URL, "/documents")
            print(f"Fetching documents from: {url} (attempt {attempt}/{max_retries})")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                documents = response.json()
                # Enrich with document info if needed
                print(f"Successfully fetched {len(documents)} documents")
                return documents
            
            # Handle server errors with retries
            elif response.status_code >= 500:
                print(f"Server error ({response.status_code}): {response.text[:200]}...")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"Max retries reached for documents endpoint")
                    return []
            
            # Handle client errors (no retry)
            elif response.status_code == 404:
                print(f"Documents endpoint not found (404)")
                return []
            elif response.status_code in (401, 403):
                print(f"Authentication error ({response.status_code})")
                return []
            else:
                print(f"Unexpected status code: {response.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"Timeout error on attempt {attempt}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Max retries reached after timeout")
                return []
        except requests.exceptions.ConnectionError:
            print(f"Connection error on attempt {attempt}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Max retries reached after connection errors")
                return []
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return []
    
    return []

@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_chat_sessions():
    """Get all chat sessions from the API."""
    print(f"CACHE MISS: get_chat_sessions() called at {datetime.now().isoformat()}")
    overall_start_time = time.time()
    api_call_duration = 0
    api_error_container = None
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            url = join_api_url(API_BASE_URL, "/chat/sessions")
            print(f"Fetching chat sessions from: {url} (attempt {attempt}/{max_retries})")
            
            api_start_time = time.time() # Time the actual API call
            response = requests.get(url, timeout=10) # Increased timeout slightly
            api_call_duration = time.time() - api_start_time
            print(f"API call took {api_call_duration:.4f}s")
            
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
                    retry_delay *= 2
                    continue
            
            # Handle other non-200 status codes
            if response.status_code != 200:
                print(f"Non-200 response: {response.status_code} - {response.text[:200]}...")
                
                if attempt < max_retries and response.status_code >= 500:
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
            result = response.json()
            print(f"get_chat_sessions() SUCCESS. Total time: {(time.time() - overall_start_time):.4f}s")
            return result
            
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
                    st.error("Request timed out accessing sessions.")
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
                    st.error("Connection failed accessing sessions.")
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
                    st.error(f"Error accessing sessions: {str(e)}")
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
        st.error("Failed to fetch sessions after multiple attempts.")
    except:
        # If we're not in a Streamlit context, ignore the UI error
        pass
    return []

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_chat_session(session_id):
    """Get a chat session by ID."""
    print(f"CACHE MISS: get_chat_session(session_id={session_id}) called at {datetime.now().isoformat()}")
    overall_start_time = time.time()
    api_call_duration = 0
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
            
            api_start_time = time.time() # Time the API call
            response = requests.get(url, timeout=5)
            api_call_duration = time.time() - api_start_time
            print(f"API call took {api_call_duration:.4f}s")
            
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
            result = response.json()
            print(f"get_chat_session() SUCCESS. Total time: {(time.time() - overall_start_time):.4f}s")
            return result
            
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
                    st.error("Request timed out accessing session.")
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
                    st.error("Connection failed accessing session.")
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
                    st.error(f"Error accessing session: {str(e)}")
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
        st.error("Failed to fetch session after multiple attempts.")
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

def handle_create_session_submit():
    """Callback function executed when the new chat session form is submitted."""
    key_prefix = st.session_state.create_session_key_prefix # Get prefix from session state

    # Retrieve form values using their keys
    session_name = st.session_state[f"{key_prefix}_name"]
    selected_docs = st.session_state[f"{key_prefix}_docs"]
    selected_provider = st.session_state[f"{key_prefix}_provider"]
    selected_model = st.session_state[f"{key_prefix}_model"]

    # --- Input Validation ---
    if not selected_docs:
        st.error("Please select at least one document.") # Use st.error for direct feedback
        st.session_state.create_session_success = False
        return # Stop processing

    # --- Auto-generate name if needed ---
    if not session_name:
        documents = get_documents() # Fetch only if needed for name generation
        if len(selected_docs) == 1:
            doc_info = next((d for d in documents if d["id"] == selected_docs[0]), None)
            if doc_info:
                metadata = doc_info.get("metadata", {})
                doc_title = metadata.get("title") or \
                            doc_info.get("title") or \
                            doc_info.get("original_filename") or \
                            doc_info.get("filename", "").split('/')[-1] or \
                            f"Document {selected_docs[0][:8]}"
                session_name = f"Chat with {doc_title}"
            else:
                 session_name = f"Chat Session {datetime.now().strftime('%Y-%m-%d_%H%M')}"
        else:
             session_name = f"Multi-doc Chat ({len(selected_docs)}) {datetime.now().strftime('%Y-%m-%d_%H%M')}"
        # Store generated name back into the widget state if needed, though not strictly necessary
        # st.session_state[f"{key_prefix}_name"] = session_name

    # --- API Call --- # Show status while creating
    with st.spinner("Creating chat session..."): 
        result = create_chat_session(\
            document_ids=selected_docs,\
            name=session_name,\
            llm_provider=selected_provider,\
            llm_model=selected_model\
        )

    # --- Handle Result --- 
    if result and "id" in result:
        st.session_state.current_session_id = result["id"]
        st.session_state.newly_created_session = True
        st.session_state.current_view = "main" # Switch view back to main
        # Clear caches for sessions and the specific new session
        get_chat_sessions.clear()
        if "current_session_cache" in st.session_state:
            del st.session_state.current_session_cache
        st.toast(f"Session '{session_name}' created successfully!", icon="✅")
        st.session_state.create_session_success = True
        # No st.rerun() needed here, Streamlit reruns automatically after callback
    else:
        st.error("Failed to create chat session. Please check logs or try again.")
        st.session_state.create_session_success = False

def create_direct_chat_session(key_prefix="main_create"):
    """Renders the form for creating a new chat session, using callbacks."""
    # Store the key_prefix in session_state so the callback can access it
    st.session_state.create_session_key_prefix = key_prefix

    documents = get_documents() # Fetch documents for the form

    with st.form(key=f"{key_prefix}_new_chat_form"):
        session_name = st.text_input(
            "Session Name (Optional)",
            key=f"{key_prefix}_name",
            placeholder="Leave blank to auto-generate"
        )

        if documents:
            doc_options = []
            for doc in documents:
                metadata = doc.get("metadata", {})
                doc_title = metadata.get("title") or \
                            doc.get("title") or \
                            doc.get("original_filename") or \
                            doc.get("filename", "").split('/')[-1] or \
                            f"Document {doc['id'][:8]}"
                doc_options.append({"id": doc["id"], "name": doc_title})
            doc_options.sort(key=lambda x: x["name"])

            st.multiselect(
                "Select Documents",
                options=[doc["id"] for doc in doc_options],
                format_func=lambda doc_id: next((doc["name"] for doc in doc_options if doc["id"] == doc_id), doc_id),
                key=f"{key_prefix}_docs"
            )
        else:
            st.warning("No documents available for selection.")
            # Disable submit button or handle appropriately if no docs is critical

        # LLM Selection
        col1, col2 = st.columns(2)
        with col1:
            provider_options = list(LLM_PROVIDERS.keys())
            st.selectbox(
                "LLM Provider",
                options=provider_options,
                format_func=lambda x: LLM_PROVIDERS.get(x, {}).get("display_name", x),
                index=provider_options.index(settings.DEFAULT_LLM_PROVIDER) if settings.DEFAULT_LLM_PROVIDER in provider_options else 0,
                key=f"{key_prefix}_provider"
            )
        with col2:
            selected_provider_key = f"{key_prefix}_provider"
            # Need to access the provider value directly for dynamic model list
            # Note: This might still cause a partial rerun when provider changes, but it's contained
            current_provider = st.session_state.get(selected_provider_key, settings.DEFAULT_LLM_PROVIDER)
            provider_models = LLM_PROVIDERS.get(current_provider, {}).get("models", [])
            # Ensure default model exists in the list, otherwise use the first model
            default_model_val = settings.DEFAULT_LLM_MODEL
            model_index = 0
            if default_model_val in provider_models:
                model_index = provider_models.index(default_model_val)
            elif provider_models:
                 default_model_val = provider_models[0] # Fallback to first model

            st.selectbox(
                "Model",
                options=provider_models,
                index=model_index,
                key=f"{key_prefix}_model"
            )

        # Use the callback for form submission
        submitted = st.form_submit_button("Create Session", on_click=handle_create_session_submit)

    # Check the success flag set by the callback (optional, for post-submission actions outside the form)
    # success = st.session_state.pop('create_session_success', None)
    # if success is True:
    #     # Actions after successful creation (e.g., clearing other state)
    #     pass
    # elif success is False:
    #     # Actions after failed creation
    #     pass

    # This function now primarily renders the form. 
    # The actual creation logic is in the callback.
    # It implicitly returns None. We can check st.session_state.create_session_success if needed.
    return st.session_state.get('create_session_success', None)

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

def render_session_selector():
    """Renders the session selection dropdown and buttons."""
    if not st.session_state.get("chat_sessions"): 
        sessions = get_chat_sessions()
        if sessions:
            try:
                sessions.sort(key=lambda s: datetime.fromisoformat(s.get('updated_at', '1970-01-01T00:00:00+00:00').replace('Z', '+00:00')), reverse=True)
            except Exception as e:
                print(f"Error sorting sessions by date: {e}")
            st.session_state.chat_sessions = sessions
        else:
            st.session_state.chat_sessions = [] 

    sessions = st.session_state.chat_sessions
    current_session_id = st.session_state.current_session_id

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        if sessions:
            session_options = {
                s["id"]: f"{s.get('name', 'Unnamed')} ({format_datetime(s.get('updated_at', ''))})"
                for s in sessions
            }
            display_options = {"": "--- Select a Session ---"} | session_options
            options_keys = list(display_options.keys())
            current_index = 0
            if current_session_id in options_keys:
                current_index = options_keys.index(current_session_id)

            st.selectbox(
                "Select Chat Session",
                options=options_keys,
                format_func=lambda x: display_options.get(x, x),
                key="session_selector_widget", 
                index=current_index,
                on_change=select_session_callback,
                label_visibility="collapsed"
            )
        else:
            st.info("No chat sessions.") 

    with col2:
        st.button("➕ New Chat", key="new_chat_btn", on_click=switch_view, args=("new_chat",), use_container_width=True)

    with col3:
        st.button("🔄 Refresh", key="refresh_btn", on_click=refresh_sessions_callback, use_container_width=True)

def render_chat_page(limited_mode=False):
    """Renders the main chat area for the selected session, optimized with form input."""
    current_session_id = st.session_state.get("current_session_id")
    if not current_session_id:
        st.warning("No session selected.")
        return 

    # --- Get Current Session Data --- 
    current_session = None
    cached_session = st.session_state.get("current_session_cache")
    needs_fetch = False
    if limited_mode:
        if isinstance(cached_session, dict) and cached_session.get("id") == current_session_id:
            current_session = cached_session
        else:
             st.warning("Session data not available in limited mode cache.")
             return
    elif not isinstance(cached_session, dict) or cached_session.get("id") != current_session_id:
        needs_fetch = True
    else:
        current_session = cached_session

    if needs_fetch and not limited_mode:
         with st.spinner(f"Loading session {current_session_id[:8]}..."):
             fetched_session = get_chat_session(current_session_id)
             if fetched_session:
                 st.session_state.current_session_cache = fetched_session
                 current_session = fetched_session
             else:
                 st.session_state.current_session_cache = None
                 st.error(f"Failed to load session {current_session_id}. It might have been deleted.")
                 return 

    if not current_session:
         st.error("Could not display session data.")
         return

    # --- Header and Session Info --- 
    st.subheader(f"{current_session.get('name', 'Unnamed Chat')}") # Use subheader below main title
    with st.expander("Session Info & Actions", expanded=False):
        col1, col2 = st.columns([2,1])
        with col1:
            st.caption(f"ID: {current_session.get('id')}")
            st.markdown(f"**LLM:** {current_session.get('llm_provider', 'N/A')} / {current_session.get('llm_model', 'N/A')}")
            doc_ids = current_session.get("document_ids", [])
            st.markdown(f"**Documents ({len(doc_ids)}):** {', '.join(d[:8]+'...' for d in doc_ids)}")
            st.caption(f"Last Updated: {format_datetime(current_session.get('updated_at', ''))}")
        with col2:
             if st.session_state.get("confirm_delete", False):
                 st.warning("Confirm Deletion:")
                 c1, c2 = st.columns(2)
                 c1.button("✅ Yes, Delete", key="confirm_delete_yes", on_click=confirm_delete_session, type="primary")
                 c2.button("❌ No, Cancel", key="confirm_delete_no", on_click=cancel_delete_session)
             else:
                 st.button("🗑️ Delete Session", key="delete_session_btn", on_click=handle_delete_session, use_container_width=True, disabled=limited_mode)

    # Display Messages
    messages = current_session.get("messages", [])
    message_container = st.container(height=500) 
    with message_container:
        if not messages:
            st.info("No messages yet. Send one below!")
        else:
            for message in messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["text"])

    # Chat Input Form 
    if not limited_mode:
        with st.form(key="chat_input_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_area(
                    "Your message:",
                    key="chat_input_widget",
                    height=75,
                    placeholder="Type your message here...",
                    label_visibility="collapsed"
                )
                st.slider("Context window", 1, 10, 5, key="context_window_widget",
                          help="Number of previous messages to include for context")
            with col2:
                 st.form_submit_button("Send", on_click=handle_send_message, use_container_width=True)
    else:
        st.info("Chat input disabled in limited mode.")

# --- Main Application Entry Point ---
def chat_interface():
    """Main application entry point."""
    # Initialize session state
    SessionState.initialize()
    
    # Get containers
    containers = SessionState.get("containers")
    
    # Render title
    with containers["title"]:
        st.title("Chat with Your Documents")
    
    # Check API health
    api_working = APIClient.check_health()
    SessionState.set("api_working", api_working)
    
    # Render main content area
    with containers["main_area"]:
        current_view = SessionState.get("current_view", "main")
        
        if current_view == "new_chat":
            UIComponents.render_new_chat_form()
        else:  # main view
            UIComponents.render_session_selector()
            if SessionState.get("current_session_id"):
                UIComponents.render_chat_page()
    
    print("End of chat_interface()")

def show_error_recovery(issue):
    # Implementation of show_error_recovery function
    pass

if __name__ == "__main__":
    chat_interface() 