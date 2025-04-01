from app.frontend.api import APIClient
from app.frontend.state import SessionState


class Callbacks:
    """Handles all callback functions for UI interactions."""
    
    @staticmethod
    def switch_view(view_name: str):
        """Switch the current view."""
        SessionState.set("current_view", view_name)
    
    @staticmethod
    def select_session():
        """Handle session selection."""
        selected_id = st.session_state.get("session_selector_widget")
        if selected_id:
            SessionState.set("current_session_id", selected_id)
            SessionState.set("current_view", "main")
    
    @staticmethod
    def refresh_sessions():
        """Refresh chat sessions list."""
        sessions = APIClient.get_chat_sessions()
        if sessions:
            SessionState.set("chat_sessions", sessions)
    
    @staticmethod
    def handle_delete_session():
        """Handle session deletion request."""
        SessionState.set("confirm_delete", True)
    
    @staticmethod
    def confirm_delete_session():
        """Confirm and execute session deletion."""
        current_session_id = SessionState.get("current_session_id")
        if current_session_id:
            if APIClient.delete_chat_session(current_session_id):
                SessionState.set("deletion_succeeded", True)
                SessionState.set("current_session_id", None)
                SessionState.set("current_session_cache", None)
                Callbacks.refresh_sessions()
            SessionState.set("confirm_delete", False)
    
    @staticmethod
    def cancel_delete_session():
        """Cancel session deletion."""
        SessionState.set("confirm_delete", False)
    
    @staticmethod
    def handle_send_message():
        """Handle sending a message."""
        message = st.session_state.get("message_input", "").strip()
        if not message:
            return
            
        current_session_id = SessionState.get("current_session_id")
        if not current_session_id:
            return
            
        SessionState.set("sending_message", True)
        try:
            response = APIClient.send_message(current_session_id, message)
            if response:
                SessionState.set("current_session_cache", response)
        finally:
            SessionState.set("sending_message", False) 