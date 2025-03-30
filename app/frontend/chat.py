import os
import json
import time
import requests
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import urljoin
import base64
import re
from PIL import Image
import io
import sys
import enum
from enum import Enum, auto
from typing import Dict, List, Any, Union, Optional

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
        response = requests.get(urljoin(API_BASE_URL, "/chat/sessions"))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching chat sessions: {str(e)}")
        return []


def get_chat_session(session_id):
    """Get a chat session by ID."""
    try:
        response = requests.get(urljoin(API_BASE_URL, f"/chat/sessions/{session_id}"))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching chat session: {str(e)}")
        return None


def create_chat_session(document_id=None, name=None):
    """Create a new chat session."""
    try:
        payload = {}
        if document_id:
            payload["document_id"] = document_id
        if name:
            payload["name"] = name
            
        response = requests.post(
            urljoin(API_BASE_URL, "/chat/sessions"),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error creating chat session: {str(e)}")
        return None


def delete_chat_session(session_id):
    """Delete a chat session."""
    try:
        response = requests.delete(urljoin(API_BASE_URL, f"/chat/sessions/{session_id}"))
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error deleting chat session: {str(e)}")
        return False


def send_message(session_id, message, context_window=5):
    """Send a message to a chat session."""
    try:
        response = requests.post(
            urljoin(API_BASE_URL, f"/chat/sessions/{session_id}/messages"),
            params={"context_window": context_window},
            json={"text": message}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return None


def get_documents():
    """Get all documents from the API."""
    try:
        # This assumes you have an endpoint that returns all documents
        # If not, you'll need to adapt this function
        url = urljoin(API_BASE_URL, "/documents")
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # It's possible there's no endpoint to get all documents
        # You might need to retrieve document info from another source
        return []


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


def chat_interface():
    """Streamlit interface for document chat."""
    st.title("Chat with Your Documents")
    
    # Initialize session state for chat
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = get_chat_sessions()
        
    if "current_session_id" not in st.session_state:
        # Set default session if available
        if st.session_state.chat_sessions:
            st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
        else:
            st.session_state.current_session_id = None
    
    # Sidebar for session management
    with st.sidebar:
        st.header("Chat Sessions")
        
        # Button to create new session
        if st.button("New Chat Session"):
            # Get documents for selection
            documents = get_documents()
            
            # Use a form for the new session
            with st.form("new_session_form"):
                session_name = st.text_input("Session Name", 
                                            placeholder="My Chat Session")
                
                # Document selection
                document_options = [(doc["id"], doc["original_filename"]) 
                                   for doc in documents if doc["status"] == "processed"]
                
                if document_options:
                    document_dict = {f"{name} (ID: {id})": id for id, name in document_options}
                    document_dict["None"] = None
                    selected_doc = st.selectbox("Select Document", 
                                               options=list(document_dict.keys()))
                    document_id = document_dict[selected_doc]
                else:
                    st.warning("No processed documents available")
                    document_id = None
                
                submit = st.form_submit_button("Create")
                
                if submit:
                    # Create the session
                    new_session = create_chat_session(
                        document_id=document_id,
                        name=session_name
                    )
                    
                    if new_session:
                        # Refresh the session list
                        st.session_state.chat_sessions = get_chat_sessions()
                        st.session_state.current_session_id = new_session["id"]
                        st.experimental_rerun()
        
        # Session selection
        if st.session_state.chat_sessions:
            session_options = {
                session["name"]: session["id"] 
                for session in st.session_state.chat_sessions
            }
            
            selected_session = st.selectbox(
                "Select Session",
                options=list(session_options.keys()),
                index=list(session_options.values()).index(st.session_state.current_session_id) 
                if st.session_state.current_session_id in session_options.values() else 0
            )
            
            st.session_state.current_session_id = session_options[selected_session]
            
            # Delete session button
            if st.button("Delete Session"):
                if delete_chat_session(st.session_state.current_session_id):
                    st.success("Session deleted successfully")
                    # Refresh the session list
                    st.session_state.chat_sessions = get_chat_sessions()
                    if st.session_state.chat_sessions:
                        st.session_state.current_session_id = st.session_state.chat_sessions[0]["id"]
                    else:
                        st.session_state.current_session_id = None
                    st.experimental_rerun()
        else:
            st.info("No chat sessions available. Create a new one to get started.")
    
    # Main chat interface
    if st.session_state.current_session_id:
        # Get current session
        current_session = get_chat_session(st.session_state.current_session_id)
        
        if current_session:
            # Display session information
            document_id = current_session.get("document_id")
            if document_id:
                st.markdown(f"**Document ID:** {document_id}")
            
            # Display messages
            messages = current_session.get("messages", [])
            
            for message in messages:
                with st.chat_message(message["role"]):
                    if message["role"] == "user":
                        # User messages are simple
                        st.markdown(message["text"])
                    else:
                        # Assistant messages may have visualizations
                        visualize_response(
                            query=messages[messages.index(message)-1]["text"] if messages.index(message) > 0 else "",
                            response_text=message["text"],
                            metadata=message.get("metadata")
                        )
            
            # Chat input
            if user_input := st.chat_input("Type your message..."):
                # Add user message to chat
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                # Process the message and get response
                with st.spinner("Thinking..."):
                    updated_session = send_message(
                        st.session_state.current_session_id,
                        user_input
                    )
                    
                    if updated_session:
                        # Get the last message (the response)
                        messages = updated_session.get("messages", [])
                        if messages and messages[-1]["role"] == "assistant":
                            with st.chat_message("assistant"):
                                response = messages[-1]
                                visualize_response(
                                    query=user_input,
                                    response_text=response["text"],
                                    metadata=response.get("metadata")
                                )
        else:
            st.error("Error loading chat session")
    else:
        st.info("Select a chat session from the sidebar or create a new one to get started.")


if __name__ == "__main__":
    chat_interface() 