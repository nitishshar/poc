import base64
import os
import time
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
import streamlit as st

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

def format_size(size_bytes):
    """Format file size from bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_datetime(dt_str):
    """Format datetime string to human-readable format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def get_all_documents():
    """Get all documents from the API."""
    try:
        response = requests.get(join_api_url(API_BASE_URL, "/documents"))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching documents: {str(e)}")
        return []


def delete_document(document_id):
    """Delete a document from the API."""
    try:
        response = requests.delete(join_api_url(API_BASE_URL, f"/documents/{document_id}"))
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error deleting document: {str(e)}")
        return False


def download_original_document(document_id):
    """Download the original document."""
    url = join_api_url(API_BASE_URL, f"/documents/{document_id}/original")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error downloading document: {str(e)}")
        return None


def document_manager_ui():
    """Streamlit interface for document management."""
    st.title("Document Management")
    
    # Fetch documents
    with st.spinner("Loading documents..."):
        documents = get_all_documents()
    
    if not documents:
        st.info("No documents found. Upload documents using the Upload Document page.")
        return
    
    # Create a DataFrame for display
    doc_data = []
    for doc in documents:
        doc_data.append({
            "ID": doc["id"],
            "Filename": doc["original_filename"],
            "Type": doc["file_type"],
            "Size": format_size(doc["file_size"]),
            "Status": doc["status"],
            "Upload Date": format_datetime(doc["upload_time"]),
            "Progress": doc["processing_progress"]
        })
    
    df = pd.DataFrame(doc_data)
    
    # Add filters
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        # Filter by status
        status_options = ["All"] + sorted(list(set(df["Status"])))
        selected_status = st.selectbox("Status", status_options)
        
    with col2:
        # Filter by file type
        type_options = ["All"] + sorted(list(set(df["Type"])))
        selected_type = st.selectbox("File Type", type_options)
    
    # Apply filters
    filtered_df = df.copy()
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["Status"] == selected_status]
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["Type"] == selected_type]
    
    # Show document count
    st.caption(f"Showing {len(filtered_df)} of {len(df)} documents")
    
    # Display documents in a table
    st.subheader("Documents")
    
    # Create a custom display for each document
    for _, doc in filtered_df.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{doc['Filename']}**")
                st.caption(f"ID: {doc['ID']}")
            
            with col2:
                st.markdown(f"**Status:** {doc['Status']}")
                st.caption(f"Type: {doc['Type']}")
            
            with col3:
                st.markdown(f"**Size:** {doc['Size']}")
                st.caption(f"Uploaded: {doc['Upload Date']}")
            
            with col4:
                # Action buttons
                if doc["Status"] == "processed":
                    st.button("View", key=f"view_{doc['ID']}", 
                              on_click=lambda doc_id=doc["ID"]: st.session_state.update({"current_document_id": doc_id, "page": "Document Status"}))
                
                # Download button
                doc_content = download_original_document(doc['ID'])
                if doc_content:
                    b64 = base64.b64encode(doc_content).decode()
                    download_link = f'<a href="data:application/octet-stream;base64,{b64}" download="{doc["Filename"]}">Download</a>'
                    st.markdown(download_link, unsafe_allow_html=True)
                
                # Delete button with confirmation
                if st.button("Delete", key=f"delete_{doc['ID']}"):
                    st.session_state[f"confirm_delete_{doc['ID']}"] = True
                
                if st.session_state.get(f"confirm_delete_{doc['ID']}", False):
                    st.warning(f"Are you sure you want to delete {doc['Filename']}?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes", key=f"yes_{doc['ID']}"):
                            if delete_document(doc['ID']):
                                st.success("Document deleted successfully")
                                st.session_state[f"confirm_delete_{doc['ID']}"] = False
                                time.sleep(1)
                                st.experimental_rerun()
                    with col2:
                        if st.button("No", key=f"no_{doc['ID']}"):
                            st.session_state[f"confirm_delete_{doc['ID']}"] = False
                            st.experimental_rerun()
            
            # Show progress bar for documents in processing
            if doc["Status"] == "processing":
                st.progress(doc['Progress'])
            
            st.markdown("---")
    
    # Refresh button
    if st.button("Refresh Document List"):
        st.experimental_rerun()


if __name__ == "__main__":
    document_manager_ui() 