"""Tests for the main chat interface."""

import pytest

from app.frontend.api import APIClient
from app.frontend.chat import chat_interface
from app.frontend.components import SessionState


@pytest.mark.usefixtures("mock_env_vars")
def test_chat_interface_initialization(app_test, monkeypatch):
    """Test chat interface initialization."""
    def mock_check_health():
        return True
    
    monkeypatch.setattr(APIClient, "check_health", mock_check_health)
    
    # Initialize the interface
    chat_interface()
    
    # Check if basic elements are present
    assert "Chat with Your Documents" in app_test.get_text()
    assert SessionState.get("view") == "main"
    assert SessionState.get("api_healthy") is True

@pytest.mark.usefixtures("mock_env_vars")
def test_chat_interface_api_unhealthy(app_test, monkeypatch):
    """Test chat interface behavior when API is unhealthy."""
    def mock_check_health():
        return False
    
    monkeypatch.setattr(APIClient, "check_health", mock_check_health)
    
    # Initialize the interface
    chat_interface()
    
    # Check if error message is shown
    assert "API is not available" in app_test.get_text()
    assert SessionState.get("api_healthy") is False

@pytest.mark.usefixtures("mock_env_vars")
def test_chat_interface_new_chat_view(app_test):
    """Test chat interface in new chat view."""
    SessionState.initialize()
    SessionState.set("view", "new_chat")
    SessionState.set("api_healthy", True)
    
    # Initialize the interface
    chat_interface()
    
    # Check if new chat form elements are present
    assert "Select Documents" in app_test.get_text()
    assert "LLM Provider" in app_test.get_text()

@pytest.mark.usefixtures("mock_env_vars")
def test_chat_interface_main_view_no_session(app_test, monkeypatch):
    """Test chat interface in main view without selected session."""
    def mock_get_chat_sessions():
        return []
    
    monkeypatch.setattr(APIClient, "get_chat_sessions", mock_get_chat_sessions)
    
    SessionState.initialize()
    SessionState.set("view", "main")
    SessionState.set("api_healthy", True)
    
    # Initialize the interface
    chat_interface()
    
    # Check if no sessions message is shown
    assert "No chat sessions found" in app_test.get_text()

@pytest.mark.usefixtures("mock_env_vars")
def test_chat_interface_main_view_with_session(app_test, monkeypatch, sample_chat_session):
    """Test chat interface in main view with selected session."""
    def mock_get_chat_sessions():
        return [sample_chat_session]
    
    monkeypatch.setattr(APIClient, "get_chat_sessions", mock_get_chat_sessions)
    
    SessionState.initialize()
    SessionState.set("view", "main")
    SessionState.set("api_healthy", True)
    SessionState.set("selected_session", sample_chat_session)
    
    # Initialize the interface
    chat_interface()
    
    # Check if session content is shown
    assert sample_chat_session["name"] in app_test.get_text()
    for message in sample_chat_session["messages"]:
        assert message["content"] in app_test.get_text()

@pytest.mark.usefixtures("mock_env_vars")
def test_chat_interface_error_handling(app_test, monkeypatch):
    """Test chat interface error handling."""
    def mock_get_chat_sessions():
        raise Exception("Test error")
    
    monkeypatch.setattr(APIClient, "get_chat_sessions", mock_get_chat_sessions)
    
    SessionState.initialize()
    SessionState.set("view", "main")
    SessionState.set("api_healthy", True)
    
    # Initialize the interface
    chat_interface()
    
    # Check if error message is shown
    assert "An error occurred" in app_test.get_text() 