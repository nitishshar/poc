import streamlit as st

from app.frontend.api import APIClient
from app.frontend.state import SessionState
from app.frontend.utils import format_file_size


def bare_bones_upload_page():
    """Extremely simplified upload page to avoid blank screen issues."""
    try:
        st.title("Upload Documents")
        st.write("Add documents to your knowledge base for semantic search and chat.")
        
        # Use a stable key for file uploader to prevent state loss
        file_uploader_key = SessionState.get("file_uploader_key", "persistent_file_uploader")
        
        uploaded_files = st.file_uploader(
            "Select document files",
            type=["pdf", "txt", "doc", "docx", "csv"],
            accept_multiple_files=True,
            key=file_uploader_key
        )
        
        if uploaded_files:
            st.write(f"Selected {len(uploaded_files)} files:")
            for file in uploaded_files:
                st.write(f"📄 {file.name} ({format_file_size(file.size)})")
            
            if st.button("Process Files", type="primary"):
                with st.spinner("Processing files..."):
                    successful_uploads = 0
                    failed_uploads = 0
                    
                    for file in uploaded_files:
                        try:
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
                                successful_uploads += 1
                            else:
                                error_msg = response.get("error", "Unknown error") if response else "Failed to get response from API"
                                st.error(f"Error uploading {file.name}: {error_msg}")
                                failed_uploads += 1
                        except Exception as e:
                            st.error(f"Error uploading {file.name}: {str(e)}")
                            st.code(str(e))
                            failed_uploads += 1
                    
                    # Show appropriate summary messages
                    if successful_uploads > 0:
                        st.success(f"Successfully processed {successful_uploads} files")
                    
                    if failed_uploads > 0:
                        st.error(f"Failed to process {failed_uploads} files")
        else:
            st.info("Please select files to upload")
            
        # Navigation buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Documents", use_container_width=True):
                SessionState.set("current_view", "documents")
                st.rerun()
        with col2:
            if st.button("View Status", use_container_width=True):
                SessionState.set("current_view", "status")
                st.rerun()
    except Exception as e:
        st.error(f"Error in upload page: {str(e)}")
        st.code(str(e)) 