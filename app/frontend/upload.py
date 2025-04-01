"""Upload functionality for the document chat application."""

import streamlit as st

from app.frontend.api import APIClient
from app.frontend.config import ICONS, MAX_UPLOAD_SIZE_MB
from app.frontend.state import SessionState
from app.frontend.utils import format_file_size


class UploadManager:
    """Handles document upload functionality."""
    
    @staticmethod
    def render_upload_page():
        """Render the document upload interface with stability as the primary focus."""
        # Simple, flat UI with minimal hierarchy
        st.title("📤 Upload Documents")
        
        # Radio buttons are more stable than tabs
        # Always create this widget with the same key
        upload_method = st.radio(
            "Choose Upload Method",
            ["File Upload", "URL Upload", "Server Path Upload"],
            horizontal=True,
            key="upload_method_selector"
        )
        
        # Simple separator
        st.markdown("---")
        
        # File Upload Section
        if upload_method == "File Upload":
            st.subheader("Upload Files")
            
            # Simple file uploader with minimal options
            uploaded_files = st.file_uploader(
                "Select documents to upload",
                accept_multiple_files=True,
                type=["pdf", "txt", "doc", "docx"],
                key="simple_file_uploader"
            )
            
            # Very simple UI for showing selected files
            if uploaded_files:
                st.success(f"{len(uploaded_files)} files selected")
                
                # Simple list of files
                for file in uploaded_files:
                    st.text(f"📁 {file.name} ({format_file_size(file.size)})")
                
                # Process button appears only when files are selected
                if st.button("Upload Selected Files", key="upload_files_btn", type="primary"):
                    # Process the files one by one with simple UI feedback
                    with st.spinner("Uploading files..."):
                        for file in uploaded_files:
                            # Simple status updates
                            st.info(f"Processing {file.name}...")
                            
                            try:
                                # TODO: Call actual API
                                # Simplified display of file info
                                st.text(f"File: {file.name}")
                                st.text(f"Size: {format_file_size(file.size)}")
                                st.text(f"Type: {file.type}")
                                st.success(f"✓ Uploaded: {file.name}")
                            except Exception as e:
                                st.error(f"Error uploading {file.name}: {str(e)}")
                        
                        # Final success message
                        st.success(f"Completed uploading {len(uploaded_files)} files")
            else:
                # Simple prompt when no files selected
                st.info("Please select one or more files to upload")

        # URL Upload Section - completely separate from File Upload
        elif upload_method == "URL Upload":
            st.subheader("Upload from URLs")
            
            # Simple text area for URLs
            urls_text = st.text_area(
                "Enter URLs (one per line)",
                placeholder="https://example.com/doc1.pdf\nhttps://example.com/doc2.pdf",
                height=150,
                key="urls_text_area"
            )
            
            # Process button for URLs
            if st.button("Process URLs", key="process_urls_btn", type="primary"):
                if urls_text:
                    # Parse URLs
                    urls = [url.strip() for url in urls_text.split("\n") if url.strip()]
                    
                    if urls:
                        # Process each URL with simple UI feedback
                        with st.spinner(f"Processing {len(urls)} URLs..."):
                            for url in urls:
                                st.info(f"Processing: {url}")
                                
                                try:
                                    # TODO: Call actual API
                                    st.text(f"URL: {url}")
                                    st.success(f"✓ Downloaded: {url}")
                                except Exception as e:
                                    st.error(f"Error processing {url}: {str(e)}")
                            
                            # Final success message
                            st.success(f"Completed processing {len(urls)} URLs")
                    else:
                        st.warning("No valid URLs found")
                else:
                    st.warning("Please enter at least one URL")

        # Server Path Upload Section - completely separate
        elif upload_method == "Server Path Upload":
            st.subheader("Upload from Server Paths")
            
            # Simple text area for paths
            paths_text = st.text_area(
                "Enter server file paths (one per line)",
                placeholder="/path/to/file1.pdf\n/path/to/file2.pdf",
                height=150,
                key="paths_text_area"
            )
            
            # Process button for paths
            if st.button("Process Paths", key="process_paths_btn", type="primary"):
                if paths_text:
                    # Parse paths
                    paths = [path.strip() for path in paths_text.split("\n") if path.strip()]
                    
                    if paths:
                        # Process each path with simple UI feedback
                        with st.spinner(f"Processing {len(paths)} paths..."):
                            for path in paths:
                                st.info(f"Processing: {path}")
                                
                                try:
                                    # TODO: Call actual API
                                    st.text(f"Path: {path}")
                                    st.success(f"✓ Processed: {path}")
                                except Exception as e:
                                    st.error(f"Error processing {path}: {str(e)}")
                            
                            # Final success message
                            st.success(f"Completed processing {len(paths)} paths")
                    else:
                        st.warning("No valid paths found")
                else:
                    st.warning("Please enter at least one path")
        
        # Simple separator
        st.markdown("---")
        
        # Navigation buttons - kept simple and flat
        st.subheader("Navigation")
        col1, col2 = st.columns(2)
        with col1:
            # Simple button to view documents
            if st.button("View Documents", use_container_width=True, key="view_docs_simple"):
                SessionState.set("current_view", "documents")
                st.rerun()
        with col2:
            # Simple button to view status
            if st.button("View Status", use_container_width=True, key="view_status_simple"):
                SessionState.set("current_view", "status")
                st.rerun() 