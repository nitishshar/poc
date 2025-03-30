import base64
import enum
import io
import json
import os
import re
import sys
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


def format_datetime(dt_str):
    """Format datetime string to human-readable format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def get_chat_sessions():
    """Get all chat sessions from the API."""
    try:
        response = requests.get(join_api_url(API_BASE_URL, "/chat/sessions"))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching chat sessions: {str(e)}")
        return []


def get_chat_session(session_id):
    """Get a chat session by ID."""
    try:
        # Ensure ID is properly formatted as UUID
        formatted_id = format_uuid_if_needed(session_id)
        if formatted_id != session_id:
            print(f"Reformatted session ID from {session_id} to {formatted_id}")
            
        # Try with the formatted ID
        url = join_api_url(API_BASE_URL, f"/chat/sessions/{formatted_id}")
        print(f"Getting chat session from: {url}")
        response = requests.get(url)
        
        # Log detailed response info for debugging
        print(f"Response status: {response.status_code}, Content: {response.text[:100]}...")
        
        if response.status_code != 200:
            # If it fails, try again with the original ID as fallback
            backup_url = join_api_url(API_BASE_URL, f"/chat/sessions/{session_id}")
            print(f"Trying fallback URL: {backup_url}")
            backup_response = requests.get(backup_url)
            if backup_response.status_code == 200:
                print("Fallback request succeeded")
                return backup_response.json()
            else:
                print(f"Fallback also failed: {backup_response.status_code}")
                
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching chat session: {str(e)}")
        print(f"Exception in get_chat_session: {str(e)}")
        return None


def create_chat_session(document_id=None, document_ids=None, name=None, chat_mode="completion"):
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
            return response.json()
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


def get_documents():
    """Get all documents from the API."""
    # Use session state to cache documents and reduce API calls
    cache_key = "documents_cache"
    cache_timestamp = "documents_timestamp"
    cache_ttl = 30  # seconds
    
    # Check if we need to refresh the cache
    current_time = time.time()
    if (cache_key not in st.session_state or 
        cache_timestamp not in st.session_state or 
        current_time - st.session_state[cache_timestamp] > cache_ttl):
        
        try:
            url = join_api_url(API_BASE_URL, "/documents")
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            
            # Store in cache
            st.session_state[cache_key] = response.json()
            st.session_state[cache_timestamp] = current_time
            return st.session_state[cache_key]
        except Exception as e:
            print(f"Error fetching documents: {str(e)}")
            if cache_key in st.session_state:
                # Return stale cache if available
                return st.session_state[cache_key]
            return []
    else:
        # Return cached documents
        return st.session_state[cache_key]


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


def test_chat_api():
    """Test if the chat API endpoints are available."""
    results = {}
    
    try:
        # Test chat sessions endpoint with a short timeout
        sessions_url = join_api_url(API_BASE_URL, "/chat/sessions")
        sessions_response = requests.get(sessions_url, timeout=1)
        results["sessions_status"] = sessions_response.status_code
        results["sessions_ok"] = sessions_response.status_code == 200
        return results
    except Exception as e:
        return {"error": str(e), "available": False}


def test_create_chat_session():
    """Test function to directly create a chat session with minimal parameters."""
    st.header("Test Chat Session Creation")
    
    with st.form("test_create_chat"):
        test_name = st.text_input("Test Chat Name", value="Test Chat")
        chat_mode_test = st.selectbox("Chat Mode", options=["completion", "assistant"])
        test_submit = st.form_submit_button("Create Test Session")
        
        if test_submit:
            try:
                # Create the simplest possible payload
                test_payload = {"name": test_name, "chat_mode": chat_mode_test}
                
                # Make direct request
                url = join_api_url(API_BASE_URL, "/chat/sessions")
                st.write(f"Sending test request to: {url}")
                st.write(f"Test payload: {test_payload}")
                
                response = requests.post(url, json=test_payload)
                st.write(f"Response status: {response.status_code}")
                st.write(f"Response headers: {dict(response.headers)}")
                st.write(f"Response content: {response.text}")
                
                if response.status_code in [200, 201]:
                    st.success("Test session created successfully!")
                else:
                    st.error(f"Test session creation failed with status {response.status_code}")
            except Exception as e:
                st.error(f"Test error: {str(e)}")
                st.exception(e)


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


def create_direct_chat_session(key_prefix="topbar"):
    """Create a chat session directly, with a simpler approach.
    
    Args:
        key_prefix: A prefix to use for all Streamlit widget keys to avoid key conflicts
    """
    st.subheader("Create New Chat Session")
    
    # Simple inputs for a more direct approach - use key_prefix to make keys unique
    direct_name = st.text_input("Session Name", value="Quick Chat", key=f"{key_prefix}_direct_name")
    
    # Update the chat mode radio to make it clearer these are OpenAI options
    direct_mode = st.radio(
        "OpenAI API Mode",
        options=[
            ("completion", "Chat Completions API"),
            ("assistant", "Assistant API")
        ],
        format_func=lambda x: x[1],
        horizontal=True,
        key=f"{key_prefix}_direct_mode",
        index=0 if settings.CHAT_MODE == "completion" else 1
    )[0]
    
    # Add tooltip to explain the difference
    st.info("""
    **API Mode Explanation**:
    - **Chat Completions API**: Standard chat completions with direct access to your documents.
    - **Assistant API**: Uses OpenAI's Assistant API with additional features but may process differently.
    """)
    
    # Get documents for a simple dropdown
    with st.spinner("Loading documents..."):
        documents = get_documents()
    
    doc_options = [(doc["id"], doc["original_filename"]) for doc in documents if doc["status"] == "processed"]
    
    # Multi-document selection
    if doc_options:
        st.write(f"Available documents: {len(doc_options)}")
        
        # For multi-document support
        selected_docs = []
        
        # Use a more efficient selection method - multiselect
        if settings.ENABLE_MULTI_DOCUMENT_CHAT:
            # Create a dictionary with user-friendly names as keys and actual IDs as values
            doc_display = {}
            for doc_id, doc_name in doc_options:
                # Truncate very long filenames for better display
                short_name = doc_name if len(doc_name) < 40 else doc_name[:37] + "..."
                # Create a unique key for each document
                doc_display[f"{short_name}"] = doc_id
            
            # Use multiselect for efficient multiple selection with unique key
            # Convert to list to ensure we have a stable order for the options
            doc_options_list = list(doc_display.keys())
            selected_doc_names = st.multiselect(
                "Select Documents (Multiple)",
                options=doc_options_list,
                key=f"{key_prefix}_multi_docs_select"
            )
            
            # Convert selected names back to document IDs
            for name in selected_doc_names:
                selected_docs.append(doc_display[name])
            
            # Handle maximum document limit
            max_docs = settings.MAX_DOCUMENTS_PER_CHAT
            if len(selected_docs) > max_docs:
                st.warning(f"Maximum {max_docs} documents allowed. Only the first {max_docs} will be used.")
                selected_docs = selected_docs[:max_docs]
                
            st.write(f"Selected {len(selected_docs)} documents")
        else:
            # Single document selection with unique key
            doc_dict = {"None": None}
            for doc_id, doc_name in doc_options:
                # Truncate very long filenames for better display
                short_name = doc_name if len(doc_name) < 40 else doc_name[:37] + "..."
                doc_dict[f"{short_name}"] = doc_id
            
            selected_doc_name = st.selectbox(
                "Select a Document (Optional)", 
                options=list(doc_dict.keys()),
                key=f"{key_prefix}_doc_select"
            )
            doc_id = doc_dict[selected_doc_name]
            
            if doc_id:
                selected_docs = [doc_id]
    else:
        st.warning("No processed documents available")
        selected_docs = []
    
    # Create the chat session with unique button key
    if st.button(
        "Create Chat Now", 
        key=f"{key_prefix}_direct_create", 
        use_container_width=True
    ):
        create_placeholder = st.empty()
        with st.spinner("Creating chat session..."):
            try:
                # Build a minimal payload
                payload = {
                    "name": direct_name,
                    "chat_mode": direct_mode
                }
                
                # Format document IDs 
                formatted_docs = []
                for doc_id in selected_docs:
                    if is_valid_uuid(doc_id):
                        formatted_docs.append(format_uuid_if_needed(doc_id))
                
                # Add document info based on selection
                if len(formatted_docs) == 1:
                    payload["document_id"] = formatted_docs[0]
                elif len(formatted_docs) > 1:
                    payload["document_ids"] = formatted_docs
                
                # Make the API request
                url = join_api_url(API_BASE_URL, "/chat/sessions")
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    create_placeholder.success("Chat session created successfully!")
                    
                    # Update session state
                    st.session_state.chat_sessions = get_chat_sessions()
                    st.session_state.current_session_id = result.get('id')
                    if "current_session_cache" in st.session_state:
                        del st.session_state.current_session_cache
                    
                    # Hide the create form and set a flag to show chat immediately
                    st.session_state.show_new_chat_form = False
                    st.session_state.newly_created_session = True
                    
                    # Force a rerun to show the chat interface with the new session
                    st.rerun()
                else:
                    create_placeholder.error(f"Failed to create chat session: {response.status_code}")
                    st.code(response.text)
            except Exception as e:
                create_placeholder.error(f"Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


def debug_uuid_format(uuid_str):
    """Debug and check a UUID string format."""
    try:
        # Check original string
        st.write(f"Original UUID: {uuid_str}")
        st.write(f"Length: {len(uuid_str)}")
        st.write(f"Contains dashes: {'Yes' if '-' in uuid_str else 'No'}")
        
        # Try different formats
        clean_uuid = uuid_str.replace('-', '')
        formatted_uuid = str(uuid.UUID(clean_uuid))
        st.write(f"Reformatted UUID: {formatted_uuid}")
        
        # Test API access with both formats
        original_url = join_api_url(API_BASE_URL, f"/chat/sessions/{uuid_str}")
        formatted_url = join_api_url(API_BASE_URL, f"/chat/sessions/{formatted_uuid}")
        
        # Try original
        st.write("Testing original format:")
        try:
            original_response = requests.get(original_url, timeout=5)
            st.write(f"Status: {original_response.status_code}")
            if original_response.status_code == 200:
                st.success("Original format works!")
            else:
                st.error("Original format failed")
        except Exception as e:
            st.error(f"Error with original format: {str(e)}")
        
        # Try formatted
        st.write("Testing reformatted UUID:")
        try:
            formatted_response = requests.get(formatted_url, timeout=5)
            st.write(f"Status: {formatted_response.status_code}")
            if formatted_response.status_code == 200:
                st.success("Reformatted UUID works!")
            else:
                st.error("Reformatted UUID failed")
        except Exception as e:
            st.error(f"Error with reformatted UUID: {str(e)}")
            
        return formatted_uuid
    except Exception as e:
        st.error(f"Error processing UUID: {str(e)}")
        return uuid_str


def diagnose_endpoints():
    """Directly check key API endpoints and display raw responses."""
    st.header("API Endpoint Diagnostics")
    
    # Add Document Inspector
    st.subheader("Document Inspector")
    doc_id_input = st.text_input(
        "Enter Document ID to inspect", 
        value="917d257b-7be1-43ee-9ddb-1d9a6ce7746f"
    )
    
    if st.button("Inspect Document"):
        if not doc_id_input:
            st.error("Please enter a document ID")
        else:
            st.write(f"Inspecting document: {doc_id_input}")
            # Format the ID
            formatted_id = format_uuid_if_needed(doc_id_input)
            if formatted_id != doc_id_input:
                st.info(f"Reformatted ID: {formatted_id}")
            
            # Try to fetch the document
            try:
                url = join_api_url(API_BASE_URL, f"/documents/{formatted_id}")
                st.write(f"Requesting: {url}")
                
                response = requests.get(url, timeout=5)
                st.write(f"Status code: {response.status_code}")
                
                if response.status_code == 200:
                    doc_data = response.json()
                    st.success("Document found!")
                    
                    # Display document info
                    st.json(doc_data)
                    
                    # Create a chat session with this document
                    if st.button("Create Chat with This Document"):
                        create_payload = {
                            "name": f"Chat with {doc_data.get('original_filename', 'Document')}",
                            "document_id": formatted_id,
                            "chat_mode": "completion"
                        }
                        
                        create_url = join_api_url(API_BASE_URL, "/chat/sessions")
                        create_response = requests.post(create_url, json=create_payload, timeout=5)
                        
                        if create_response.status_code in [200, 201]:
                            session_data = create_response.json()
                            st.success(f"Chat session created! ID: {session_data.get('id')}")
                            st.session_state.chat_sessions = get_chat_sessions()
                            st.session_state.current_session_id = session_data.get('id')
                            if "current_session_cache" in st.session_state:
                                del st.session_state.current_session_cache
                        else:
                            st.error(f"Failed to create chat session: {create_response.status_code}")
                            st.code(create_response.text)
                else:
                    st.error(f"Could not find document. Status: {response.status_code}")
                    
                    # Try without formatting as a fallback
                    fallback_url = join_api_url(API_BASE_URL, f"/documents/{doc_id_input}")
                    st.write(f"Trying fallback with original ID: {fallback_url}")
                    fallback_response = requests.get(fallback_url, timeout=5)
                    
                    if fallback_response.status_code == 200:
                        st.success("Document found with original ID format!")
                        fallback_data = fallback_response.json()
                        st.json(fallback_data)
                    else:
                        st.error(f"Fallback also failed: {fallback_response.status_code}")
            except Exception as e:
                st.error(f"Error fetching document: {str(e)}")
    
    # Add UUID debugging tool
    st.subheader("Debug UUID Format")
    debug_uuid = st.text_input(
        "Enter UUID to debug",
        value="917d257b-7be1-43ee-9ddb-1d9a6ce7746f"
    )
    
    if st.button("Check UUID Format"):
        formatted_uuid = debug_uuid_format(debug_uuid)
        if formatted_uuid != debug_uuid:
            st.info(f"UUID was reformatted from {debug_uuid} to {formatted_uuid}")
    
    # Add direct test for the problematic UUID
    st.subheader("Fix Specific Document Issue")
    problem_uuid = "917d257b-7be1-43ee-9ddb-1d9a6ce7746f"
    
    if st.button("Test Problematic UUID"):
        st.write(f"Testing access to problematic UUID: {problem_uuid}")
        
        # Try different formats and access methods
        test_formats = [
            problem_uuid,  # Original
            problem_uuid.lower(),  # All lowercase
            problem_uuid.upper(),  # All uppercase
            problem_uuid.replace('-', ''),  # No dashes
            str(uuid.UUID(problem_uuid.replace('-', ''))),  # Standard format
        ]
        
        # Test each format with both document and session endpoints
        for i, test_format in enumerate(test_formats):
            st.write(f"Format {i+1}: {test_format}")
            
            # Test document endpoint
            try:
                doc_url = join_api_url(API_BASE_URL, f"/documents/{test_format}")
                doc_response = requests.get(doc_url, timeout=5)
                if doc_response.status_code == 200:
                    st.success(f"✅ Document endpoint works with this format! Status: {doc_response.status_code}")
                    st.json(doc_response.json())
                else:
                    st.error(f"❌ Document endpoint failed: {doc_response.status_code}")
            except Exception as e:
                st.error(f"Document endpoint error: {str(e)}")
            
            # Test session endpoint
            try:
                session_url = join_api_url(API_BASE_URL, f"/chat/sessions/{test_format}")
                session_response = requests.get(session_url, timeout=5)
                st.write(f"Session endpoint status: {session_response.status_code}")
            except Exception as e:
                st.error(f"Session endpoint error: {str(e)}")
    
    # Check API endpoints (without nested expanders)
    st.subheader("API Endpoint Status")
    # List of key endpoints to check
    endpoints = [
        "/chat/sessions",
        "/documents",
        "/health",  # This is at base_url, not API_BASE_URL
    ]
    
    # Test each endpoint directly
    results = []
    
    # Special case for health endpoint
    base_url = API_BASE_URL
    if "/api" in base_url:
        base_url = base_url.split("/api")[0]
    
    try:
        health_url = f"{base_url}/health"
        health_response = requests.get(health_url, timeout=3)
        results.append({
            "endpoint": "/health",
            "url": health_url,
            "status": health_response.status_code,
            "working": health_response.status_code == 200,
            "content": health_response.text[:200] + "..." if len(health_response.text) > 200 else health_response.text
        })
    except Exception as e:
        results.append({
            "endpoint": "/health",
            "url": health_url,
            "status": "Error",
            "working": False,
            "content": str(e)
        })
    
    # Test API endpoints
    for endpoint in endpoints:
        if endpoint == "/health":
            continue  # Already tested
            
        try:
            url = join_api_url(API_BASE_URL, endpoint)
            response = requests.get(url, timeout=3)
            results.append({
                "endpoint": endpoint,
                "url": url,
                "status": response.status_code,
                "working": response.status_code == 200,
                "content": response.text[:200] + "..." if len(response.text) > 200 else response.text
            })
        except Exception as e:
            results.append({
                "endpoint": endpoint,
                "url": url,
                "status": "Error",
                "working": False,
                "content": str(e)
            })
    
    # Display results in a simple table format instead of expanders
    endpoints_table = []
    for result in results:
        status_icon = "✅" if result["working"] else "❌"
        endpoints_table.append({
            "Endpoint": result["endpoint"],
            "Status": f"{status_icon} {result['status']}",
            "URL": result["url"]
        })
    
    # Create a DataFrame for cleaner display
    endpoints_df = pd.DataFrame(endpoints_table)
    st.table(endpoints_df)
    
    # Add option to view response details
    selected_endpoint = st.selectbox(
        "Select endpoint to view response details:",
        options=[r["endpoint"] for r in results],
        key="endpoint_details"
    )
    
    # Show content for selected endpoint
    for result in results:
        if result["endpoint"] == selected_endpoint:
            st.write(f"Response from {result['url']}:")
            st.code(result["content"])
    
    # Test chat session creation directly
    st.subheader("Test Chat Session Creation")
    if st.button("Create Test Session"):
        try:
            payload = {"name": "Diagnostic Test Chat"}
            url = join_api_url(API_BASE_URL, "/chat/sessions")
            st.write(f"Sending request to: {url}")
            st.code(json.dumps(payload, indent=2))
            
            response = requests.post(url, json=payload, timeout=5)
            st.write(f"Status: {response.status_code}")
            st.code(response.text)
            
            if response.status_code in [200, 201]:
                st.success("Test successful!")
            else:
                st.error("Test failed!")
        except Exception as e:
            st.error(f"Error: {str(e)}")


def chat_interface():
    """Streamlit interface for document chat - simplified approach."""
    st.title("Chat with Your Documents")
    
    # API connection check
    api_working = True
    try:
        # Get the base URL without the /api path for health check
        base_url = API_BASE_URL
        if "/api" in base_url:
            base_url = base_url.split("/api")[0]
        
        health_url = f"{base_url}/health"
        api_check = requests.get(health_url, timeout=2)
        api_working = api_check.status_code == 200
        
        # Display connection status
        if api_working:
            st.success("✅ Connected to API backend")
        else:
            st.error("❌ API health check failed - backend is not responding")
            
    except Exception as e:
        st.error(f"❌ API connection error: {str(e)}")
        api_working = False
    
    if not api_working:
        st.error("⚠️ API is not connected. Chat functionality requires the backend API to be running.")
        st.info(f"Please ensure the backend server is running at: {base_url}")
        return
    
    # Initialize session state for chat
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = get_chat_sessions()
        
    if "current_session_id" not in st.session_state:
        # Set default session if available
        if st.session_state.chat_sessions:
            st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
        else:
            st.session_state.current_session_id = None
    
    # Call the chat page renderer directly
    render_chat_page()


def render_chat_page():
    """Render the chat interface page using a simplified approach similar to the example."""
    # Check if we have a newly created session
    newly_created = st.session_state.get("newly_created_session", False)
    
    # Clear the flag to prevent it from triggering again
    if newly_created:
        st.session_state.newly_created_session = False
        st.success("Chat session created successfully! You can start chatting now.")
    
    st.header("Chat with Your Documents")
    
    # Cache the current session to avoid repeated API calls
    current_session = None
    if st.session_state.current_session_id:
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
        st.subheader("Your Chat Sessions")
        
        # Add a refresh button for sessions
        if st.button("🔄 Refresh Sessions", key="refresh_sessions", use_container_width=True):
            st.session_state.chat_sessions = get_chat_sessions()
            if "current_session_cache" in st.session_state:
                del st.session_state.current_session_cache
            st.success("Sessions refreshed!")
        
        # Add a button to create a new session
        if st.button("➕ New Session", key="new_session_button", use_container_width=True):
            st.session_state.show_new_chat_form = True
        
        # Show new chat form if requested
        if st.session_state.get("show_new_chat_form", False):
            with st.expander("Create New Session", expanded=True):
                create_direct_chat_session(key_prefix="sidebar")
                if st.button("Cancel", key="cancel_new_session"):
                    st.session_state.show_new_chat_form = False
        
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
            
            # Create a clean visual selection
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
            
        else:
            st.info("No chat sessions available. Create a new session to get started.")
    
    # Right column: Chat interface (simplified like the example)
    with chat_cols[1]:
        if st.session_state.current_session_id and current_session:
            st.header(f"Chat: {current_session['name']}")
            
            # Display basic chat info
            chat_mode = current_session.get("chat_mode", settings.CHAT_MODE)
            document_ids = current_session.get("document_ids", [])
            if not document_ids and current_session.get("document_id"):
                document_ids = [current_session["document_id"]]
                
            # Display info in a more compact way
            info_cols = st.columns(3)
            with info_cols[0]:
                mode_display = "OpenAI Chat Completions" if chat_mode == "completion" else "OpenAI Assistant"
                st.markdown(f"**Mode:** {mode_display}")
            with info_cols[1]:
                st.markdown(f"**Documents:** {len(document_ids)}")
            with info_cols[2]:
                # Add a refresh button for just this session
                if st.button("🔄 Refresh Chat", key="refresh_current_chat"):
                    if "current_session_cache" in st.session_state:
                        del st.session_state.current_session_cache
            
            # Display messages - SIMPLIFIED APPROACH following the example
            messages = current_session.get("messages", [])
            
            # Display all messages
            for message in messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["text"])
            
            # Chat input - SIMPLIFIED like the example
            if prompt := st.chat_input("Type your message..."):
                # Add user message to chat history and display immediately
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Send message to backend and get response
                with st.spinner("Thinking..."):
                    updated_session = send_message(
                        st.session_state.current_session_id,
                        prompt
                    )
                    
                    if updated_session:
                        # Update session cache
                        st.session_state.current_session_cache = updated_session
                        
                        # Get the assistant's response
                        messages = updated_session.get("messages", [])
                        if messages and messages[-1]["role"] == "assistant":
                            with st.chat_message("assistant"):
                                response = messages[-1]
                                st.markdown(response["text"])
                    else:
                        st.error("Failed to get a response. Please try again.")
        
        elif st.session_state.current_session_id and not current_session:
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
            
            # Add a quick direct creation form
            st.markdown("### Create New Chat Session")
            create_direct_chat_session(key_prefix="main")


if __name__ == "__main__":
    chat_interface() 