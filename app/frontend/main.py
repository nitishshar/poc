import os
import json
import time
import requests
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
from urllib.parse import urljoin
import io
import base64
from PIL import Image, ImageDraw
import fitz  # PyMuPDF for PDF manipulation

# Import the chat interface
from chat import chat_interface
# Import the document manager
from document_manager import document_manager_ui

# Set page configuration
st.set_page_config(
    page_title="Document Processing Service",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")


# Helper functions
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


def format_datetime(dt):
    """Format datetime to human-readable format."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_document_status(document_id):
    """Get document processing status from API."""
    url = urljoin(API_BASE_URL, f"/documents/{document_id}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching document status: {str(e)}")
        return None


def get_document_content(document_id, page=None, section=None):
    """Get processed document content from API."""
    url = urljoin(API_BASE_URL, f"/documents/{document_id}/content")
    params = {}
    if page is not None:
        params["page"] = page
    if section is not None:
        params["section"] = section
        
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching document content: {str(e)}")
        return []


def get_document_tables(document_id, page=None):
    """Get document tables from API."""
    url = urljoin(API_BASE_URL, f"/documents/{document_id}/tables")
    params = {}
    if page is not None:
        params["page"] = page
        
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching document tables: {str(e)}")
        return []


def search_embeddings(document_id, query, limit=5, page=None):
    """Search document embeddings."""
    url = urljoin(API_BASE_URL, f"/documents/{document_id}/embeddings")
    params = {
        "query": query,
        "limit": limit
    }
    if page is not None:
        params["page"] = page
        
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error searching embeddings: {str(e)}")
        return {"collection_info": {}, "results": []}


def download_original_document(document_id):
    """Download the original document."""
    url = urljoin(API_BASE_URL, f"/documents/{document_id}/original")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error downloading document: {str(e)}")
        return None


def highlight_pdf_sections(pdf_content, text_chunks):
    """Highlight sections in a PDF based on text chunks with coordinates."""
    try:
        # Load PDF from bytes
        pdf_file = io.BytesIO(pdf_content)
        pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
        
        # Create a list to hold modified pages
        modified_pages = []
        
        # Process each page that has text chunks with coordinates
        for chunk in text_chunks:
            if chunk.get("page_number") and chunk.get("coordinates"):
                page_num = chunk["page_number"] - 1  # 0-indexed
                if page_num >= 0 and page_num < len(pdf_document):
                    page = pdf_document[page_num]
                    
                    # Parse coordinates
                    coords = chunk["coordinates"]
                    if isinstance(coords, str):
                        # Convert string representation to dict
                        coords = json.loads(coords.replace("'", "\""))
                    
                    x1, y1, x2, y2 = coords.get("x1", 0), coords.get("y1", 0), coords.get("x2", 0), coords.get("y2", 0)
                    
                    # Add highlight annotation
                    highlight_rect = fitz.Rect(x1, y1, x2, y2)
                    annot = page.add_highlight_annot(highlight_rect)
                    annot.set_colors({"stroke": (1, 1, 0)})  # Yellow highlight
                    annot.update()
                    
                    # Track modified pages
                    if page_num not in modified_pages:
                        modified_pages.append(page_num)
        
        # Save the modified PDF
        output_pdf = io.BytesIO()
        pdf_document.save(output_pdf)
        pdf_document.close()
        
        # Return the modified PDF content
        return output_pdf.getvalue()
    except Exception as e:
        st.error(f"Error highlighting PDF: {str(e)}")
        return pdf_content


# Sidebar navigation
st.sidebar.title("Document Processing Service")
page = st.sidebar.radio("Navigation", ["Upload Document", "Document Status", "Search Embeddings", "Chat with Documents", "Document Manager"])

if page == "Upload Document":
    st.title("Document Upload & Processing")

    # Create tabs for two different upload experiences
    upload_tabs = st.tabs(["Standard Upload", "Advanced Upload Options"])
    
    with upload_tabs[0]:
        # Simplified unified upload form
        with st.form("unified_upload_form"):
            st.subheader("Upload Documents")
            st.write("Choose one of the following upload methods:")

            # Upload method selection
            upload_method = st.radio(
                "Upload Method",
                ["Upload File(s)", "From Server Path", "From URL"],
                horizontal=True
            )
            
            # Container for the selected method
            if upload_method == "Upload File(s)":
                uploaded_files = st.file_uploader(
                    "Select Document(s)", 
                    type=["pdf", "docx", "doc", "txt", "csv", "xlsx", "xls"],
                    help="Select one or more documents to upload and process",
                    accept_multiple_files=True
                )
            
            elif upload_method == "From Server Path":
                file_path = st.text_input(
                    "Enter file path on server", 
                    help="Enter the full path to a file on the server (e.g., C:/documents/example.pdf)"
                )
                st.caption("💡 Use forward slashes (/) instead of backslashes (\\) for Windows paths")
            
            else:  # From URL
                file_url = st.text_input(
                    "Enter document URL", 
                    help="Enter the URL of a document to download and process (e.g., https://example.com/document.pdf)"
                )
            
            process_immediately = st.checkbox(
                "Process immediately after upload", 
                value=True,
                help="If checked, document processing will start immediately after upload"
            )
            
            submit_button = st.form_submit_button("Upload & Process")
            
            if submit_button:
                if upload_method == "Upload File(s)" and uploaded_files:
                    with st.spinner("Uploading document(s)..."):
                        if len(uploaded_files) == 1:
                            # Single file upload
                            files = {"file": (uploaded_files[0].name, uploaded_files[0].getvalue())}
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/upload"),
                                params={"process_immediately": str(process_immediately).lower()},
                                files=files
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                st.success(f"Document uploaded successfully. Document ID: {result['document_id']}")
                                
                                # Store document ID in session state
                                if "document_ids" not in st.session_state:
                                    st.session_state.document_ids = []
                                
                                st.session_state.document_ids.append(result["document_id"])
                                
                                # Set current document
                                st.session_state.current_document_id = result["document_id"]
                                
                                # Store a flag to redirect to status page after form submission
                                st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error uploading document: {response.text}")
                        else:
                            # Multiple files upload
                            # Create files list in the format expected by FastAPI
                            files = []
                            for file in uploaded_files:
                                files.append(("files", (file.name, file.getvalue(), 'application/octet-stream')))
                                
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/upload-multiple"),
                                params={"process_immediately": str(process_immediately).lower()},
                                files=files
                            )
                            
                            if response.status_code == 200:
                                results = response.json()
                                
                                # Display summary
                                st.success(f"Successfully uploaded {len([r for r in results if r.get('document_id')])} of {len(uploaded_files)} documents")
                                
                                # Display details in an expander
                                with st.expander("Upload Details"):
                                    for i, result in enumerate(results):
                                        if result.get("document_id"):
                                            st.success(f"{uploaded_files[i].name}: {result['message']}")
                                            
                                            # Store document ID in session state
                                            if "document_ids" not in st.session_state:
                                                st.session_state.document_ids = []
                                            
                                            st.session_state.document_ids.append(result["document_id"])
                                            
                                            # Set the last successfully uploaded document as current
                                            st.session_state.current_document_id = result["document_id"]
                                        else:
                                            st.error(f"{uploaded_files[i].name}: {result['message']}")
                                
                                # Redirect to status page if at least one file was uploaded successfully
                                if any(r.get("document_id") for r in results):
                                    # Store a flag to redirect to status page after form submission
                                    st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error uploading documents: {response.text}")
                    
                elif upload_method == "From Server Path" and file_path:
                    with st.spinner("Processing document..."):
                        # Normalize file path (replace backslashes with forward slashes)
                        normalized_path = file_path.replace('\\', '/')
                        
                        data = {
                            "file_path": normalized_path,
                            "file_url": None,
                            "process_immediately": process_immediately
                        }
                        
                        try:
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/upload-by-path"),
                                json=data
                            )
                            
                            # Debug information
                            with st.expander("Request Details (for troubleshooting)"):
                                st.write(f"**Request URL:** {urljoin(API_BASE_URL, '/documents/upload-by-path')}")
                                st.write(f"**Request Body:** {data}")
                                st.write(f"**Response Status:** {response.status_code}")
                                st.write(f"**Response Content:** {response.text}")
                            
                            if response.status_code in [200, 201, 202]:
                                result = response.json()
                                st.success(f"Document processed successfully. Document ID: {result['document_id']}")
                                
                                # Store document ID in session state
                                if "document_ids" not in st.session_state:
                                    st.session_state.document_ids = []
                                
                                st.session_state.document_ids.append(result["document_id"])
                                
                                # Set current document
                                st.session_state.current_document_id = result["document_id"]
                                
                                # Store a flag to redirect to status page after form submission
                                st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error processing document: {response.text}")
                                
                                # Help suggestions
                                if response.status_code == 404:
                                    st.warning("The API endpoint was not found. Please check that the backend server is running and accessible.")
                                    st.info("Try these troubleshooting steps:")
                                    st.markdown("1. Make sure the FastAPI backend is running (check terminal)")
                                    st.markdown("2. Verify the API Base URL is correct")
                                    st.markdown("3. Check if there are any firewall or network issues")
                                elif "File not found" in response.text:
                                    st.warning("The file path could not be found on the server.")
                                    st.info("Try these troubleshooting steps:")
                                    st.markdown("1. Make sure the file exists at the exact path specified")
                                    st.markdown("2. Remember that the path must be accessible to the server, not your local machine")
                                    st.markdown("3. Try using an absolute path instead of a relative path")
                                    st.markdown("4. Check file permissions (the server must have read access)")
                        except Exception as e:
                            st.error(f"Error connecting to API: {str(e)}")
                            st.info("Check that the backend server is running and accessible.")
                
                elif upload_method == "From URL" and file_url:
                    with st.spinner("Downloading and processing document..."):
                        data = {
                            "file_path": None,
                            "file_url": file_url,
                            "process_immediately": process_immediately
                        }
                        
                        try:
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/upload-by-path"),
                                json=data
                            )
                            
                            if response.status_code in [200, 201, 202]:
                                result = response.json()
                                st.success(f"Document downloaded and processed successfully. Document ID: {result['document_id']}")
                                
                                # Store document ID in session state
                                if "document_ids" not in st.session_state:
                                    st.session_state.document_ids = []
                                
                                st.session_state.document_ids.append(result["document_id"])
                                
                                # Set current document
                                st.session_state.current_document_id = result["document_id"]
                                
                                # Store a flag to redirect to status page after form submission
                                st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error downloading and processing document: {response.text}")
                                if response.status_code == 404:
                                    st.warning("The API endpoint was not found. Please check that the backend server is running and accessible.")
                        except Exception as e:
                            st.error(f"Error connecting to API: {str(e)}")
                            st.info("Check that the backend server is running and accessible.")
                else:
                    if upload_method == "Upload File(s)":
                        st.warning("Please select at least one file to upload.")
                    elif upload_method == "From Server Path":
                        st.warning("Please enter a file path on the server.")
                    else:
                        st.warning("Please enter a URL for the document.")
        
        # Check if we need to redirect to the status page after form submission
        if st.session_state.get("redirect_to_status"):
            st.session_state.redirect_to_status = False
            st.button("View Document Status", on_click=lambda: st.experimental_rerun())
        
        # API connection status
        with st.expander("API Connection Settings"):
            current_api_url = st.text_input("API Base URL", value=API_BASE_URL, key="api_base_url_unified")
            if current_api_url != API_BASE_URL:
                API_BASE_URL = current_api_url
            
            if st.button("Test API Connection", key="test_api_unified"):
                try:
                    response = requests.get(urljoin(API_BASE_URL, "/documents"))
                    if response.status_code == 200:
                        st.success(f"✅ Successfully connected to API at {API_BASE_URL}")
                    else:
                        st.error(f"❌ API returned status code: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Failed to connect to API: {str(e)}")
    
    with upload_tabs[1]:
        # Keep the existing tabbed interface for advanced users
        advanced_tabs = st.tabs(["Upload File", "Local Path", "URL"])
        
        with advanced_tabs[0]:
            # File upload form
            with st.form("upload_form"):
                uploaded_files = st.file_uploader("Select Document(s)", 
                    type=["pdf", "docx", "doc", "txt", "csv", "xlsx", "xls"],
                    help="Select one or more documents to upload and process",
                    accept_multiple_files=True)
                
                process_immediately = st.checkbox("Process immediately after upload", value=True,
                                                help="If checked, document processing will start immediately after upload")
                
                submit_button = st.form_submit_button("Upload Document(s)")
                
                if submit_button and uploaded_files:
                    with st.spinner("Uploading document(s)..."):
                        if len(uploaded_files) == 1:
                            # Single file upload
                            files = {"file": (uploaded_files[0].name, uploaded_files[0].getvalue())}
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/upload"),
                                params={"process_immediately": str(process_immediately).lower()},
                                files=files
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                st.success(f"Document uploaded successfully. Document ID: {result['document_id']}")
                                
                                # Store document ID in session state
                                if "document_ids" not in st.session_state:
                                    st.session_state.document_ids = []
                                
                                st.session_state.document_ids.append(result["document_id"])
                                
                                # Set current document
                                st.session_state.current_document_id = result["document_id"]
                                
                                # Store a flag to redirect to status page after form submission
                                st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error uploading document: {response.text}")
                        else:
                            # Multiple files upload
                            # Create files list in the format expected by FastAPI
                            files = []
                            for file in uploaded_files:
                                files.append(("files", (file.name, file.getvalue(), 'application/octet-stream')))
                                
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/upload-multiple"),
                                params={"process_immediately": str(process_immediately).lower()},
                                files=files
                            )
                            
                            if response.status_code == 200:
                                results = response.json()
                                
                                # Display summary
                                st.success(f"Successfully uploaded {len([r for r in results if r.get('document_id')])} of {len(uploaded_files)} documents")
                                
                                # Display details in an expander
                                with st.expander("Upload Details"):
                                    for i, result in enumerate(results):
                                        if result.get("document_id"):
                                            st.success(f"{uploaded_files[i].name}: {result['message']}")
                                            
                                            # Store document ID in session state
                                            if "document_ids" not in st.session_state:
                                                st.session_state.document_ids = []
                                            
                                            st.session_state.document_ids.append(result["document_id"])
                                            
                                            # Set the last successfully uploaded document as current
                                            st.session_state.current_document_id = result["document_id"]
                                        else:
                                            st.error(f"{uploaded_files[i].name}: {result['message']}")
                            
                                # Redirect to status page if at least one file was uploaded successfully
                                if any(r.get("document_id") for r in results):
                                    # Store a flag to redirect to status page after form submission
                                    st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error uploading documents: {response.text}")
            
            # Check if we need to redirect to the status page after form submission
            if st.session_state.get("redirect_to_status"):
                st.session_state.redirect_to_status = False
                st.button("View Document Status", on_click=lambda: st.experimental_rerun())
        
        with advanced_tabs[1]:
            # Local file path form
            with st.form("local_path_form"):
                st.write("Enter local file path(s) on the server")
                
                # Option for single file or multiple files
                upload_type = st.radio("Upload type", ["Single File", "Multiple Files"], key="path_upload_type")
                
                if upload_type == "Single File":
                    # Single file input
                    file_path = st.text_input(
                        "Enter file path", 
                        help="Enter the full path to a file on the server (e.g., C:/documents/example.pdf)"
                    )
                    # Display path format guidance
                    st.caption("💡 Use forward slashes (/) instead of backslashes (\\) for Windows paths")
                    file_paths = [file_path] if file_path else []
                else:
                    # Multiple files input with textarea
                    file_paths_text = st.text_area(
                        "Enter file paths (one per line)", 
                        help="Enter full paths to files on the server, one path per line"
                    )
                    # Display path format guidance
                    st.caption("💡 Use forward slashes (/) instead of backslashes (\\) for Windows paths")
                    # Split by newline and filter out empty lines
                    file_paths = [path.strip() for path in file_paths_text.split('\n') if path.strip()]
                    
                    # Option to upload a directory
                    col1, col2 = st.columns(2)
                    with col1:
                        directory_path = st.text_input(
                            "Or enter a directory path",
                            help="Enter a directory path to process all supported files in that directory"
                        )
                    
                    with col2:
                        if directory_path:
                            include_subdirs = st.checkbox(
                                "Include subdirectories",
                                help="If checked, files in subdirectories will also be processed"
                            )
                
                # Move the API settings expander outside the form to fix the button issue
                
                process_immediately = st.checkbox("Process immediately after upload", value=True,
                                                help="If checked, document processing will start immediately after upload",
                                                key="path_process")
                
                submit_button = st.form_submit_button("Process Document(s)")
                
                if submit_button:
                    # Process directory if specified
                    if upload_type == "Multiple Files" and directory_path:
                        with st.spinner(f"Scanning directory {directory_path}..."):
                            st.info(f"Scanning {'recursively' if include_subdirs else 'directory'} - this might take a moment for large directories")
                            
                            # Fall back to JSON endpoint for directory scanning
                            data = {
                                "directory_path": directory_path,
                                "include_subdirectories": include_subdirs,
                                "process_immediately": process_immediately
                            }
                            
                            # Call a custom request handler for this
                            st.info("Directory scanning support requires the API to be running. Please ensure the backend is running.")
                            st.warning("Directory scanning is not fully implemented in this demo.")
                    
                    # Process specific files if listed
                    if file_paths:
                        with st.spinner(f"Processing {len(file_paths)} document(s)..."):
                            # Normalize file paths (replace backslashes with forward slashes)
                            normalized_paths = [path.replace('\\', '/') for path in file_paths]
                            
                            if len(normalized_paths) == 1:
                                # Single file processing
                                data = {
                                    "file_path": normalized_paths[0],
                                    "file_url": None,
                                    "process_immediately": process_immediately
                                }
                                
                                # Call the API
                                try:
                                    response = requests.post(
                                        urljoin(API_BASE_URL, "/documents/upload-by-path"),
                                        json=data
                                    )
                                    
                                    # Debug information
                                    with st.expander("Request Details (for troubleshooting)"):
                                        st.write(f"**Request URL:** {urljoin(API_BASE_URL, '/documents/upload-by-path')}")
                                        st.write(f"**Request Body:** {data}")
                                        st.write(f"**Response Status:** {response.status_code}")
                                        st.write(f"**Response Content:** {response.text}")
                                    
                                    if response.status_code in [200, 201, 202]:
                                        result = response.json()
                                        st.success(f"Document processed successfully. Document ID: {result['document_id']}")
                                        
                                        # Store document ID in session state
                                        if "document_ids" not in st.session_state:
                                            st.session_state.document_ids = []
                                        
                                        st.session_state.document_ids.append(result["document_id"])
                                        
                                        # Set current document
                                        st.session_state.current_document_id = result["document_id"]
                                        
                                        # Store a flag to redirect to status page after form submission
                                        st.session_state.redirect_to_status = True
                                    else:
                                        st.error(f"Error processing document: {response.text}")
                                        
                                        # Help suggestions
                                        if response.status_code == 404:
                                            st.warning("The API endpoint was not found. Please check that the backend server is running and accessible.")
                                            st.info("Try these troubleshooting steps:")
                                            st.markdown("1. Make sure the FastAPI backend is running (check terminal)")
                                            st.markdown("2. Verify the API Base URL in the settings above")
                                            st.markdown("3. Check if there are any firewall or network issues")
                                        elif "File not found" in response.text:
                                            st.warning("The file path could not be found on the server.")
                                            st.info("Try these troubleshooting steps:")
                                            st.markdown("1. Make sure the file exists at the exact path specified")
                                            st.markdown("2. Remember that the path must be accessible to the server, not your local machine")
                                            st.markdown("3. Try using an absolute path instead of a relative path")
                                            st.markdown("4. Check file permissions (the server must have read access)")
                                except Exception as e:
                                    st.error(f"Error connecting to API: {str(e)}")
                                    st.info("Check that the backend server is running and accessible.")
                            else:
                                # Multiple files processing
                                batch_data = []
                                for path in normalized_paths:
                                    batch_data.append({
                                        "file_path": path,
                                        "file_url": None,
                                        "process_immediately": process_immediately
                                    })
                                
                                # Call the batch API
                                try:
                                    response = requests.post(
                                        urljoin(API_BASE_URL, "/documents/batch-upload"),
                                        json=batch_data
                                    )
                                    
                                    # Debug information
                                    with st.expander("Request Details (for troubleshooting)"):
                                        st.write(f"**Request URL:** {urljoin(API_BASE_URL, '/documents/batch-upload')}")
                                        st.write(f"**Request Body (first item):** {batch_data[0] if batch_data else 'Empty'}")
                                        st.write(f"**Response Status:** {response.status_code}")
                                        st.write("**Response Content (truncated):**")
                                        st.write(response.text[:500] + "..." if len(response.text) > 500 else response.text)
                                    
                                    if response.status_code == 200:
                                        results = response.json()
                                        
                                        # Count successful uploads
                                        success_count = len([r for r in results if r.get("document_id")])
                                        
                                        # Display summary
                                        st.success(f"Successfully processed {success_count} of {len(file_paths)} documents")
                                        
                                        # Display details in an expander
                                        with st.expander("Processing Details"):
                                            for i, result in enumerate(results):
                                                if result.get("document_id"):
                                                    st.success(f"{file_paths[i]}: {result['message']}")
                                                    
                                                    # Store document ID in session state
                                                    if "document_ids" not in st.session_state:
                                                        st.session_state.document_ids = []
                                                    
                                                    st.session_state.document_ids.append(result["document_id"])
                                                    
                                                    # Set the last successfully uploaded document as current
                                                    st.session_state.current_document_id = result["document_id"]
                                                else:
                                                    st.error(f"{file_paths[i]}: {result['message']}")
                                        
                                        # Redirect to status page if at least one file was processed successfully
                                        if success_count > 0:
                                            # Store a flag to redirect to status page after form submission
                                            st.session_state.redirect_to_status = True
                                    else:
                                        st.error(f"Error processing documents: {response.text}")
                                        
                                        # Help suggestions
                                        if response.status_code == 404:
                                            st.warning("The API endpoint was not found. Please check that the backend server is running and accessible.")
                                except Exception as e:
                                    st.error(f"Error connecting to API: {str(e)}")
                                    st.info("Check that the backend server is running and accessible.")
                    else:
                        st.warning("Please enter at least one file path to process.")
            
            # Check if we need to redirect to the status page after form submission
            if st.session_state.get("redirect_to_status"):
                st.session_state.redirect_to_status = False
                st.button("View Document Status", on_click=lambda: st.experimental_rerun())
            
            # Add API status check - moved outside the form
            with st.expander("API Connection Settings"):
                current_api_url = st.text_input("API Base URL", value=API_BASE_URL, key="api_base_url")
                if current_api_url != API_BASE_URL:
                    API_BASE_URL = current_api_url
                
                if st.button("Test API Connection"):
                    try:
                        response = requests.get(urljoin(API_BASE_URL, "/documents"))
                        if response.status_code == 200:
                            st.success(f"✅ Successfully connected to API at {API_BASE_URL}")
                        else:
                            st.error(f"❌ API returned status code: {response.status_code}")
                    except Exception as e:
                        st.error(f"❌ Failed to connect to API: {str(e)}")
        
        with advanced_tabs[2]:
            # URL form
            with st.form("url_form"):
                # Option for single URL or multiple URLs
                url_upload_type = st.radio("Upload type", ["Single URL", "Multiple URLs"], key="url_upload_type")
                
                if url_upload_type == "Single URL":
                    # Single URL input
                    file_url = st.text_input("Enter document URL", 
                                            help="Enter the URL of a document to download and process (e.g., https://example.com/document.pdf)")
                    file_urls = [file_url] if file_url else []
                else:
                    # Multiple URLs input with textarea
                    file_urls_text = st.text_area(
                        "Enter document URLs (one per line)", 
                        help="Enter URLs of documents to download and process, one URL per line"
                    )
                    # Split by newline and filter out empty lines
                    file_urls = [url.strip() for url in file_urls_text.split('\n') if url.strip()]
                
                process_immediately = st.checkbox("Process immediately after upload", value=True,
                                                help="If checked, document processing will start immediately after upload",
                                                key="url_process")
                
                submit_button = st.form_submit_button("Download & Process")
                
                if submit_button and file_urls:
                    with st.spinner(f"Downloading and processing {len(file_urls)} document(s)..."):
                        if len(file_urls) == 1:
                            # Single URL processing
                            data = {
                                "file_path": None,
                                "file_url": file_urls[0],
                                "process_immediately": process_immediately
                            }
                            
                            # Call the API
                            try:
                                response = requests.post(
                                    urljoin(API_BASE_URL, "/documents/upload"),
                                    data={"file_url": file_urls[0], "process_immediately": str(process_immediately).lower()}
                                )
                            except Exception:
                                # Fall back to JSON endpoint
                                response = requests.post(
                                    urljoin(API_BASE_URL, "/documents/upload-by-path"),
                                    json=data
                                )
                            
                            if response.status_code in [200, 201, 202]:
                                result = response.json()
                                st.success(f"Document downloaded and processed successfully. Document ID: {result['document_id']}")
                                
                                # Store document ID in session state
                                if "document_ids" not in st.session_state:
                                    st.session_state.document_ids = []
                                
                                st.session_state.document_ids.append(result["document_id"])
                                
                                # Set current document
                                st.session_state.current_document_id = result["document_id"]
                                
                                # Store a flag to redirect to status page after form submission
                                st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error downloading and processing document: {response.text}")
                        else:
                            # Multiple URLs processing
                            batch_data = []
                            for url in file_urls:
                                batch_data.append({
                                    "file_path": None,
                                    "file_url": url,
                                    "process_immediately": process_immediately
                                })
                            
                            # Call the batch API
                            response = requests.post(
                                urljoin(API_BASE_URL, "/documents/batch-upload"),
                                json=batch_data
                            )
                            
                            if response.status_code == 200:
                                results = response.json()
                                
                                # Count successful downloads
                                success_count = len([r for r in results if r.get("document_id")])
                                
                                # Display summary
                                st.success(f"Successfully downloaded and processed {success_count} of {len(file_urls)} documents")
                                
                                # Display details in an expander
                                with st.expander("Processing Details"):
                                    for i, result in enumerate(results):
                                        if result.get("document_id"):
                                            st.success(f"{file_urls[i]}: {result['message']}")
                                            
                                            # Store document ID in session state
                                            if "document_ids" not in st.session_state:
                                                st.session_state.document_ids = []
                                            
                                            st.session_state.document_ids.append(result["document_id"])
                                            
                                            # Set the last successfully downloaded document as current
                                            st.session_state.current_document_id = result["document_id"]
                                        else:
                                            st.error(f"{file_urls[i]}: {result['message']}")
                                
                                # Redirect to status page if at least one URL was processed successfully
                                if success_count > 0:
                                    # Store a flag to redirect to status page after form submission
                                    st.session_state.redirect_to_status = True
                            else:
                                st.error(f"Error downloading and processing documents: {response.text}")
                elif submit_button:
                    st.warning("Please enter at least one URL to process.")
            
            # Check if we need to redirect to the status page after form submission
            if st.session_state.get("redirect_to_status"):
                st.session_state.redirect_to_status = False
                st.button("View Document Status", on_click=lambda: st.experimental_rerun())

# Display recent documents if available
if page == "Upload Document" and "document_ids" in st.session_state and st.session_state.document_ids:
    st.subheader("Recent Documents")
    
    for doc_id in reversed(st.session_state.document_ids[-5:]):  # Show last 5 documents
        doc_status = get_document_status(doc_id)
        
        if doc_status:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{doc_status['original_filename']}**")
            with col2:
                st.write(f"Status: {doc_status['status']}")
            with col3:
                if st.button("View Status", key=f"view_{doc_id}"):
                    st.session_state.current_document_id = doc_id
                    st.experimental_rerun()

elif page == "Document Status":
    st.title("Document Processing Status")
    
    # Document selection
    if "document_ids" in st.session_state and st.session_state.document_ids:
        # Get current document ID, either from selection or session state
        document_options = st.session_state.document_ids
        
        if "current_document_id" in st.session_state:
            default_index = document_options.index(st.session_state.current_document_id) if st.session_state.current_document_id in document_options else 0
        else:
            default_index = 0
            
        selected_document = st.selectbox(
            "Select Document", 
            options=document_options,
            index=default_index,
            format_func=lambda x: get_document_status(x)["original_filename"] if get_document_status(x) else x
        )
        
        st.session_state.current_document_id = selected_document
        
        # Get document status
        doc_status = get_document_status(selected_document)
        
        if doc_status:
            # Calculate processing time
            processing_time = None
            if doc_status.get("processing_steps"):
                start_time = None
                end_time = None
                
                for step in doc_status["processing_steps"]:
                    if step.get("start_time") and (start_time is None or datetime.fromisoformat(step["start_time"].replace('Z', '+00:00')) < start_time):
                        start_time = datetime.fromisoformat(step["start_time"].replace('Z', '+00:00'))
                    
                    if step.get("end_time") and (end_time is None or datetime.fromisoformat(step["end_time"].replace('Z', '+00:00')) > end_time):
                        end_time = datetime.fromisoformat(step["end_time"].replace('Z', '+00:00'))
                
                if start_time and end_time:
                    processing_time = (end_time - start_time).total_seconds()
            
            # Document info
            st.subheader("Document Information")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Filename:** {doc_status['original_filename']}")
                st.write(f"**Type:** {doc_status['file_type']}")
                st.write(f"**Size:** {format_size(doc_status['file_size'])}")
            
            with col2:
                st.write(f"**Upload Time:** {format_datetime(doc_status['upload_time'])}")
                st.write(f"**Status:** {doc_status['status']}")
                if processing_time:
                    st.write(f"**Processing Time:** {processing_time:.2f} seconds")
                
            with col3:
                if doc_status['status'] == 'uploaded' or doc_status['status'] == 'failed':
                    if st.button("Start Processing"):
                        # Call process endpoint
                        process_url = urljoin(API_BASE_URL, f"/documents/{selected_document}/process")
                        response = requests.post(process_url)
                        if response.status_code == 202:
                            st.success("Processing started")
                            time.sleep(1)
                            st.experimental_rerun()
                        else:
                            st.error(f"Error starting processing: {response.text}")
                
                # Download original document
                if st.button("Download Original"):
                    doc_content = download_original_document(selected_document)
                    if doc_content:
                        # Convert to base64 for download
                        b64 = base64.b64encode(doc_content).decode()
                        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{doc_status["original_filename"]}">Click to download</a>'
                        st.markdown(href, unsafe_allow_html=True)
            
            # Progress visualization
            st.subheader("Processing Progress")
            progress_bar = st.progress(float(doc_status["processing_progress"]))
            
            # Display current step if processing
            if doc_status["status"] == "processing" and doc_status.get("current_step"):
                st.info(f"Current step: {doc_status['current_step']}")
            
            # If failed, show error message
            if doc_status["status"] == "failed" and doc_status.get("error_message"):
                st.error(f"Processing failed: {doc_status['error_message']}")
            
            # Processing steps visualization
            if doc_status.get("processing_steps"):
                steps_data = []
                
                for step in doc_status["processing_steps"]:
                    step_data = {
                        "Step": step["step"],
                        "Status": step["status"],
                        "Progress": step.get("progress", 0.0)
                    }
                    
                    if step.get("start_time"):
                        step_data["Start Time"] = format_datetime(step["start_time"])
                    
                    if step.get("end_time"):
                        step_data["End Time"] = format_datetime(step["end_time"])
                        
                    if step.get("error"):
                        step_data["Error"] = step["error"]
                    
                    steps_data.append(step_data)
                
                # Convert to DataFrame for display
                steps_df = pd.DataFrame(steps_data)
                
                # Create tabs for different views
                tab1, tab2 = st.tabs(["Steps Table", "Timeline"])
                
                with tab1:
                    st.dataframe(steps_df)
                
                with tab2:
                    # Create a timeline using plotly
                    if all(["Start Time" in step for step in steps_data if step["Status"] != "pending"]):
                        timeline_data = []
                        
                        for step in steps_data:
                            if step["Status"] != "pending":
                                start_time = datetime.strptime(step["Start Time"], "%Y-%m-%d %H:%M:%S")
                                end_time = datetime.strptime(step.get("End Time", step["Start Time"]), "%Y-%m-%d %H:%M:%S")
                                
                                timeline_data.append({
                                    "Task": step["Step"],
                                    "Start": start_time,
                                    "Finish": end_time,
                                    "Status": step["Status"]
                                })
                        
                        if timeline_data:
                            df = pd.DataFrame(timeline_data)
                            
                            # Create color map based on status
                            color_map = {
                                "completed": "#00FF00",  # Green
                                "failed": "#FF0000",     # Red
                                "in_progress": "#FFA500",  # Orange
                                "skipped": "#808080"     # Gray
                            }
                            
                            fig = px.timeline(
                                df, 
                                x_start="Start", 
                                x_end="Finish", 
                                y="Task",
                                color="Status",
                                color_discrete_map=color_map,
                                title="Processing Steps Timeline"
                            )
                            
                            fig.update_layout(
                                xaxis_title="Time",
                                yaxis_title="Processing Step",
                                height=400
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Timeline data not available yet.")
                    else:
                        st.info("Timeline data not available yet.")
            
            # Document content and metadata
            if doc_status["status"] == "processed":
                st.subheader("Document Content and Metadata")
                
                # Display tabs for different content views
                tabs = st.tabs(["Metadata", "Content Preview", "Tables", "Highlighted PDF"])
                
                with tabs[0]:  # Metadata
                    if doc_status.get("metadata"):
                        metadata = doc_status["metadata"]
                        
                        # Create columns for display
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Document Metadata**")
                            
                            for key in ["title", "author", "created_date", "modified_date"]:
                                if metadata.get(key):
                                    if key.endswith("_date") and isinstance(metadata[key], str):
                                        st.write(f"**{key.replace('_', ' ').title()}:** {format_datetime(metadata[key])}")
                                    else:
                                        st.write(f"**{key.replace('_', ' ').title()}:** {metadata[key]}")
                        
                        with col2:
                            st.write("**Document Statistics**")
                            
                            for key in ["page_count", "word_count", "content_type"]:
                                if metadata.get(key):
                                    st.write(f"**{key.replace('_', ' ').title()}:** {metadata[key]}")
                        
                        # Display custom metadata if available
                        if metadata.get("custom_metadata") and metadata["custom_metadata"]:
                            st.write("**Custom Metadata**")
                            
                            for key, value in metadata["custom_metadata"].items():
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    else:
                        st.info("No metadata available.")
                
                with tabs[1]:  # Content Preview
                    # Get document content
                    content = get_document_content(selected_document)
                    
                    if content:
                        # Create filter options
                        st.write("**Filter Content**")
                        
                        # Get unique page numbers and section titles
                        pages = sorted(list(set([c.get("page_number") for c in content if c.get("page_number") is not None])))
                        sections = sorted(list(set([c.get("section_title") for c in content if c.get("section_title") is not None])))
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            selected_page = st.selectbox("Page", [None] + pages, format_func=lambda x: "All Pages" if x is None else f"Page {x}")
                        
                        with col2:
                            selected_section = st.selectbox("Section", [None] + sections, format_func=lambda x: "All Sections" if x is None else x)
                        
                        # Filter content based on selection
                        filtered_content = content
                        
                        if selected_page is not None:
                            filtered_content = [c for c in filtered_content if c.get("page_number") == selected_page]
                        
                        if selected_section is not None:
                            filtered_content = [c for c in filtered_content if c.get("section_title") == selected_section]
                        
                        # Display chunks
                        st.write(f"**Content Chunks ({len(filtered_content)})**")
                        
                        for i, chunk in enumerate(filtered_content):
                            with st.expander(f"Chunk {i+1}" + (f" - {chunk['section_title']}" if chunk.get('section_title') else "")):
                                st.write(chunk["text"])
                                
                                # Show metadata
                                metadata_items = []
                                
                                if chunk.get("page_number") is not None:
                                    metadata_items.append(f"Page: {chunk['page_number']}")
                                    
                                if chunk.get("paragraph_number") is not None:
                                    metadata_items.append(f"Paragraph: {chunk['paragraph_number']}")
                                
                                if metadata_items:
                                    st.caption(" | ".join(metadata_items))
                    else:
                        st.info("No content available.")
                
                with tabs[2]:  # Tables
                    # Get document tables
                    tables = get_document_tables(selected_document)
                    
                    if tables:
                        st.write(f"**Tables ({len(tables)})**")
                        
                        # Filter by page
                        table_pages = sorted(list(set([t.get("page_number") for t in tables if t.get("page_number") is not None])))
                        selected_table_page = st.selectbox("Page", [None] + table_pages, format_func=lambda x: "All Pages" if x is None else f"Page {x}", key="table_page")
                        
                        # Filter tables based on selection
                        filtered_tables = tables
                        
                        if selected_table_page is not None:
                            filtered_tables = [t for t in filtered_tables if t.get("page_number") == selected_table_page]
                        
                        # Display tables
                        for i, table in enumerate(filtered_tables):
                            with st.expander(f"Table {i+1}" + (f" - {table['caption']}" if table.get('caption') else "")):
                                # Display header
                                if table.get("header"):
                                    st.write("**Header**")
                                    st.write(" | ".join([str(h) for h in table["header"]]))
                                
                                # Display data
                                if table.get("data"):
                                    st.write("**Data**")
                                    
                                    # Convert to DataFrame
                                    columns = table.get("header", [f"Column {i+1}" for i in range(table.get("columns", 0))])
                                    df = pd.DataFrame(table["data"], columns=columns)
                                    st.dataframe(df)
                                
                                # Show metadata
                                metadata_items = []
                                
                                if table.get("page_number") is not None:
                                    metadata_items.append(f"Page: {table['page_number']}")
                                    
                                if table.get("rows") is not None and table.get("columns") is not None:
                                    metadata_items.append(f"Size: {table['rows']}x{table['columns']}")
                                
                                if metadata_items:
                                    st.caption(" | ".join(metadata_items))
                    else:
                        st.info("No tables available.")
                
                with tabs[3]:  # Highlighted PDF
                    if doc_status["file_type"].lower() == ".pdf":
                        st.write("**PDF with Highlighted Sections**")
                        
                        # Get content with coordinates
                        content = get_document_content(selected_document)
                        filtered_content = [c for c in content if c.get("coordinates")]
                        
                        if filtered_content:
                            # Download original PDF
                            pdf_content = download_original_document(selected_document)
                            
                            if pdf_content:
                                # Highlight sections
                                highlighted_pdf = highlight_pdf_sections(pdf_content, filtered_content)
                                
                                # Display PDF
                                st.download_button(
                                    label="Download Highlighted PDF",
                                    data=highlighted_pdf,
                                    file_name=f"highlighted_{doc_status['original_filename']}",
                                    mime="application/pdf"
                                )
                                
                                # Display PDF in iframe
                                base64_pdf = base64.b64encode(highlighted_pdf).decode('utf-8')
                                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                                st.markdown(pdf_display, unsafe_allow_html=True)
                            else:
                                st.error("Error loading PDF content.")
                        else:
                            st.info("No coordinates available for highlighting.")
                    else:
                        st.info("PDF highlighting is only available for PDF documents.")
        else:
            st.error("Error loading document status.")
    else:
        st.info("No documents available. Please upload a document first.")

elif page == "Search Embeddings":
    st.title("Search Document Embeddings")
    
    # Document selection
    if "document_ids" in st.session_state and st.session_state.document_ids:
        # Get current document ID, either from selection or session state
        document_options = st.session_state.document_ids
        
        if "current_document_id" in st.session_state:
            default_index = document_options.index(st.session_state.current_document_id) if st.session_state.current_document_id in document_options else 0
        else:
            default_index = 0
            
        selected_document = st.selectbox(
            "Select Document", 
            options=document_options,
            index=default_index,
            format_func=lambda x: get_document_status(x)["original_filename"] if get_document_status(x) else x
        )
        
        st.session_state.current_document_id = selected_document
        
        # Get document status
        doc_status = get_document_status(selected_document)
        
        if doc_status and doc_status["status"] == "processed":
            st.subheader(f"Search in: {doc_status['original_filename']}")
            
            # Create search form
            with st.form("search_form"):
                query = st.text_input("Enter your search query")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    limit = st.slider("Number of results", 1, 20, 5)
                
                with col2:
                    # Get unique page numbers
                    content = get_document_content(selected_document)
                    pages = sorted(list(set([c.get("page_number") for c in content if c.get("page_number") is not None])))
                    
                    page = st.selectbox("Page filter", [None] + pages, format_func=lambda x: "All Pages" if x is None else f"Page {x}")
                
                submit_button = st.form_submit_button("Search")
                
                if submit_button and query:
                    with st.spinner("Searching..."):
                        # Search embeddings
                        results = search_embeddings(selected_document, query, limit, page)
                        
                        if results and results.get("results"):
                            st.success(f"Found {len(results['results'])} results")
                            
                            # Display collection info
                            if results.get("collection_info"):
                                st.caption(f"Collection: {results['collection_info'].get('name')} | Total chunks: {results['collection_info'].get('count')}")
                            
                            # Display results
                            for i, result in enumerate(results["results"]):
                                with st.expander(f"Result {i+1} - Relevance: {1 - result['distance']:.4f}"):
                                    st.write(result["text"])
                                    
                                    # Show metadata if available
                                    if result.get("metadata"):
                                        metadata_items = []
                                        
                                        if result["metadata"].get("page_number"):
                                            metadata_items.append(f"Page: {result['metadata']['page_number']}")
                                            
                                        if result["metadata"].get("section_title"):
                                            metadata_items.append(f"Section: {result['metadata']['section_title']}")
                                            
                                        if result["metadata"].get("is_table"):
                                            metadata_items.append("Type: Table")
                                        
                                        if metadata_items:
                                            st.caption(" | ".join(metadata_items))
                        else:
                            st.warning(f"No results found for query: {query}")
        elif doc_status and doc_status["status"] != "processed":
            st.warning(f"Document is not ready for search. Current status: {doc_status['status']}")
            
            if doc_status["status"] == "processing":
                progress_bar = st.progress(float(doc_status["processing_progress"]))
                st.info(f"Current step: {doc_status.get('current_step', 'Unknown')}")
                
                if st.button("Refresh Status"):
                    st.experimental_rerun()
            elif doc_status["status"] in ["uploaded", "failed"]:
                if st.button("Process Document"):
                    # Call process endpoint
                    process_url = urljoin(API_BASE_URL, f"/documents/{selected_document}/process")
                    response = requests.post(process_url)
                    if response.status_code == 202:
                        st.success("Processing started")
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.error(f"Error starting processing: {response.text}")
        else:
            st.error("Error loading document status.")
    else:
        st.info("No documents available. Please upload a document first.")

elif page == "Chat with Documents":
    # Display the chat interface
    chat_interface()

elif page == "Document Manager":
    # Display the document manager interface
    document_manager_ui()


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    """
    This is a document processing service that handles document ingestion, 
    semantic parsing, and vector embedding generation.
    
    - Process multi-format documents
    - Extract semantic meaning and metadata
    - Generate vector embeddings
    - Search and analyze document content
    """
)

# Environment info
st.sidebar.markdown("### Environment")
st.sidebar.text(f"API URL: {API_BASE_URL}")

# Add custom CSS
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    </style>
    """, 
    unsafe_allow_html=True
) 