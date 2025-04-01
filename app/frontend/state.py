from typing import Any, Dict

import streamlit as st


class SessionState:
    """Manages all session state variables in a centralized way."""
    
    @staticmethod
    def initialize():
        """Initialize all session state variables if they don't exist."""
        defaults = {
            "containers": {
                "title": st.container(),
                "status": st.empty(),
                "error_recovery": st.container(),
                "main_area": st.container(),
            },
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
            "create_session_success": None,
            "ws_connection": None,
            "ws_messages": {},
            "file_uploader_key": "persistent_file_uploader",
            "upload_files": None,
            "uploaded_files_metadata": []
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
                
        if "file_uploader_key" in st.session_state:
            st.session_state.file_uploader_key = st.session_state.file_uploader_key

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get a session state value with a default fallback."""
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any):
        """Set a session state value."""
        st.session_state[key] = value

    @staticmethod
    def delete(key: str):
        """Delete a session state value."""
        if key in st.session_state:
            del st.session_state[key]
            
    @staticmethod
    def preserve_file_uploader_state():
        """Critical method to ensure file uploader state is preserved across reruns.
        This addresses the blank screen issue that occurs when files are selected."""
        if "file_uploader_key" in st.session_state:
            st.session_state.file_uploader_key = st.session_state.file_uploader_key
            
        if hasattr(st.session_state, "uploaded_files") and st.session_state.uploaded_files:
            files_data = []
            for file in st.session_state.uploaded_files:
                if hasattr(file, "name") and hasattr(file, "size") and hasattr(file, "type"):
                    files_data.append({
                        "name": file.name,
                        "size": file.size,
                        "type": file.type
                    })
            if files_data:
                st.session_state.uploaded_files_metadata = files_data 