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
page = st.sidebar.radio("Navigation", ["Upload Document", "Document Status", "Search Embeddings", "Chat with Documents"])

if page == "Upload Document":
    st.title("Upload Document for Processing")
    
    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Select Document", 
                                         type=["pdf", "docx", "doc", "txt", "csv", "xlsx", "xls"],
                                         help="Select a document to upload and process")
        
        process_immediately = st.checkbox("Process immediately after upload", value=True,
                                         help="If checked, document processing will start immediately after upload")
        
        submit_button = st.form_submit_button("Upload Document")
        
        if submit_button and uploaded_file is not None:
            with st.spinner("Uploading document..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
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
                    
                    # Redirect to status page
                    st.experimental_rerun()
                else:
                    st.error(f"Error uploading document: {response.text}")
    
    # Display recent documents if available
    if "document_ids" in st.session_state and st.session_state.document_ids:
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