import os
from datetime import datetime

import streamlit as st

from app.frontend.api import APIClient
from app.frontend.bare_bones_upload_page import bare_bones_upload_page
from app.frontend.components import UIComponents
from app.frontend.state import SessionState
from app.frontend.utils import format_file_size


def create_persistent_upload_page():
    """Create a properly designed upload page that handles file uploader state correctly.
    
    This implementation focuses on stable behavior with files rather than minimalism.
    The key to avoiding blank screens is proper state management and consistent widget keys.
    """
    # Critical: Preserve file uploader state to prevent blank screens on file selection
    SessionState.preserve_file_uploader_state()
    
    # Title and description
    st.title("📤 Upload Documents")
    st.write("Add documents to your knowledge base for semantic search and chat.")
    
    # Set a stable key for the file uploader to prevent state loss
    file_uploader_key = st.session_state.file_uploader_key
    
    # Create three tabs that persist across reruns
    tab_labels = ["File Upload", "URL Import", "Server Path"]
    tabs = st.tabs(tab_labels)
    
    # File Upload tab
    with tabs[0]:
        st.subheader("Upload Files")
        
        # The critical part: Use the stable key from session state for the file uploader
        uploaded_files = st.file_uploader(
            "Select document files",
            type=["pdf", "txt", "doc", "docx", "csv"],
            accept_multiple_files=True,
            key=file_uploader_key,
            help="Select one or more files to upload"
        )
        
        # Store uploaded files in session state for persistence
        if uploaded_files:
            st.session_state.uploaded_files = uploaded_files
            
            # Show file information
            st.write(f"Selected {len(uploaded_files)} files:")
            for file in uploaded_files:
                st.write(f"📄 {file.name} ({format_file_size(file.size)})")
            
            # Process button with a unique key
            if st.button("Upload Selected Files", key="upload_btn", type="primary"):
                with st.spinner("Processing files..."):
                    for file in uploaded_files:
                        try:
                            # Call API to process the file
                            st.info(f"Processing: {file.name}")
                            # Read file content
                            file_content = file.read()
                            file_name = file.name
                            
                            # Make the actual API call to upload the file
                            response = APIClient.upload_document(
                                file_name=file_name,
                                file_content=file_content,
                                content_type=file.type
                            )
                            
                            if response and response.get("success"):
                                st.success(f"✓ Uploaded: {file.name}")
                            else:
                                error_msg = response.get("error", "Unknown error") if response else "Failed to get response from API"
                                st.error(f"Error uploading {file.name}: {error_msg}")
                        except Exception as e:
                            st.error(f"Error uploading {file.name}: {str(e)}")
                    
                    st.success(f"Successfully processed {len(uploaded_files)} files")
        else:
            st.info("Please select files to upload")

    # URL Import tab
    with tabs[1]:
        st.subheader("Import from URLs")
        
        # Use persistent keys for all widgets
        url_input = st.text_area(
            "Enter URLs (one per line)",
            key="url_input_area",
            placeholder="https://example.com/document.pdf\nhttps://example.com/another.pdf",
            height=150
        )
        
        if st.button("Import from URLs", key="url_import_btn", type="primary"):
            if url_input:
                urls = [url.strip() for url in url_input.split("\n") if url.strip()]
                if urls:
                    with st.spinner(f"Processing {len(urls)} URLs..."):
                        successful_imports = 0
                        failed_imports = 0
                        
                        for url in urls:
                            try:
                                st.info(f"Importing from: {url}")
                                # Make actual API call to process URL
                                response = APIClient.import_document_from_url(url=url)
                                if response and response.get("success"):
                                    st.success(f"✓ Imported: {url}")
                                    successful_imports += 1
                                else:
                                    error_msg = response.get("error", "Unknown error") if response else "Failed to get response from API"
                                    st.error(f"Error importing {url}: {error_msg}")
                                    failed_imports += 1
                            except Exception as e:
                                st.error(f"Error importing {url}: {str(e)}")
                                failed_imports += 1
                        
                        # Only show success if there were actual successes
                        if successful_imports > 0:
                            st.success(f"Successfully processed {successful_imports} URLs")
                        
                        # Show summary of failures if any
                        if failed_imports > 0:
                            st.error(f"Failed to process {failed_imports} URLs")
                else:
                    st.warning("No valid URLs found")
            else:
                st.warning("Please enter at least one URL")

    # Server Path tab
    with tabs[2]:
        st.subheader("Import from Server Path")
        
        # Use persistent keys for all widgets
        path_input = st.text_area(
            "Enter server file paths (one per line)",
            key="path_input_area",
            placeholder="/path/to/document.pdf\n/path/to/another.pdf",
            height=150
        )
        
        if st.button("Import from Paths", key="path_import_btn", type="primary"):
            if path_input:
                paths = [path.strip() for path in path_input.split("\n") if path.strip()]
                if paths:
                    with st.spinner(f"Processing {len(paths)} paths..."):
                        successful_imports = 0
                        failed_imports = 0
                        
                        for path in paths:
                            try:
                                st.info(f"Importing from: {path}")
                                # Make actual API call to process server path
                                response = APIClient.import_document_from_path(path=path)
                                if response and response.get("success"):
                                    st.success(f"✓ Imported: {path}")
                                    successful_imports += 1
                                else:
                                    error_msg = response.get("error", "Unknown error") if response else "Failed to get response from API"
                                    st.error(f"Error importing {path}: {error_msg}")
                                    failed_imports += 1
                            except Exception as e:
                                st.error(f"Error importing {path}: {str(e)}")
                                failed_imports += 1
                        
                        # Only show success if there were actual successes
                        if successful_imports > 0:
                            st.success(f"Successfully processed {successful_imports} paths")
                        
                        # Show summary of failures if any
                        if failed_imports > 0:
                            st.error(f"Failed to process {failed_imports} paths")
                else:
                    st.warning("No valid paths found")
            else:
                st.warning("Please enter at least one path")
    
    # Navigation buttons
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Documents", key="view_docs_btn", use_container_width=True):
            SessionState.set("current_view", "documents")
            st.rerun()
    with col2:
        if st.button("View Status", key="view_status_btn", use_container_width=True):
            SessionState.set("current_view", "status")
            st.rerun()


def main():
    """Main application entry point."""
    # Set page config
    st.set_page_config(
        page_title="Document Chat",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        /* Main container */
        .main > div {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Sidebar */
        .css-1d391kg {
            width: 24rem;
        }
        section[data-testid="stSidebar"] {
            width: 24rem !important;
            background-color: #1E1E1E;
            position: fixed;
            left: 0;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }
        section[data-testid="stSidebar"] > div {
            width: 24rem !important;
            background-color: #1E1E1E;
            padding: 2rem 1rem;
        }
        
        /* Main content positioning */
        .main .block-container {
            padding-left: 26rem;
            max-width: none;
        }
        
        /* Buttons */
        .stButton>button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        
        /* Sidebar buttons */
        .stSidebar .stButton>button {
            background-color: #2E2E2E;
            border: 1px solid #3E3E3E;
            color: #FFFFFF;
        }
        .stSidebar .stButton>button:hover {
            background-color: #3E3E3E;
            border: 1px solid #4E4E4E;
        }
        
        /* Form elements */
        .stTextInput>div>div>input {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
        .stTextArea>div>div>textarea {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #FFFFFF;
        }
        
        /* Links */
        a {
            color: #4CAF50;
        }
        a:hover {
            color: #45a049;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    SessionState.initialize()
    
    # Standard container for main content
    main_container = st.container()
    
    # Render sidebar
    with st.sidebar:
        st.title("Document Chat")
        
        # Navigation
        st.subheader("Navigation")
        
        # Main sections
        st.button(
            "💬 Chat Sessions",
            key="nav_chat",
            on_click=SessionState.set,
            args=("current_view", "main"),
            use_container_width=True,
            type="primary" if SessionState.get("current_view") == "main" else "secondary"
        )
        
        st.button(
            "📄 Document Manager",
            key="nav_docs",
            on_click=SessionState.set,
            args=("current_view", "documents"),
            use_container_width=True,
            type="primary" if SessionState.get("current_view") == "documents" else "secondary"
        )
        
        # Upload button - simple callback
        st.button(
            "📤 Upload Documents",
            key="nav_upload",
            on_click=SessionState.set,
            args=("current_view", "upload"),
            use_container_width=True,
            type="primary" if SessionState.get("current_view") == "upload" else "secondary"
        )
        
        st.button(
            "🔍 Search & Embeddings",
            key="nav_search",
            on_click=SessionState.set,
            args=("current_view", "search"),
            use_container_width=True,
            type="primary" if SessionState.get("current_view") == "search" else "secondary"
        )
        
        st.button(
            "📊 Document Status",
            key="nav_status",
            on_click=SessionState.set,
            args=("current_view", "status"),
            use_container_width=True,
            type="primary" if SessionState.get("current_view") == "status" else "secondary"
        )
        
        # Info section
        st.markdown("""
            ### About
            This application allows you to chat with your documents using various LLM providers.
            
            ### Features
            - Multiple document support
            - Multiple LLM providers
            - Context-aware responses
            - Session management
            - Real-time updates
            
            ### Environment
            - API URL: `{}`
            - Python: `{}`
            - Streamlit: `{}`
        """.format(
            os.getenv("API_BASE_URL", "http://localhost:8000/api"),
            os.getenv("PYTHON_VERSION", "Unknown"),
            st.__version__
        ))
        
        # Reset button
        if st.button("Reset Session State", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.toast("Session state reset!", icon="🔄")
            st.rerun()
    
    # Render main content in the container
    with main_container:
        try:
            # Check API health once
            api_health = APIClient.check_health()
            if not api_health and SessionState.get("current_view") != "upload":
                st.error("Backend API is not responding. Some features may be limited.")
            
            # Get current view
            current_view = SessionState.get("current_view", "main")
            
            # Render appropriate view based on the current view
            if current_view == "main":
                UIComponents.render_chat_page()
            elif current_view == "new_chat":
                UIComponents.render_new_chat_form()
            elif current_view == "documents":
                UIComponents.render_document_manager()
            elif current_view == "status":
                UIComponents.render_document_status()
            elif current_view == "upload":
                # Try the persistent version first, fallback to bare bones if it fails
                try:
                    create_persistent_upload_page()
                except Exception as e:
                    st.error(f"Error with persistent upload page: {str(e)}")
                    st.warning("Falling back to simplified upload page...")
                    bare_bones_upload_page()
            elif current_view == "search":
                UIComponents.render_search_page()
            else:
                st.error(f"Unknown view: {current_view}")
                if st.button("Return to Main View"):
                    SessionState.set("current_view", "main")
                    st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            if st.button("Return to Main View"):
                SessionState.set("current_view", "main")
                st.rerun()

if __name__ == "__main__":
    main() 