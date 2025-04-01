"""Tests for the UI components module."""

import pytest

from app.frontend.components import Callbacks, SessionState, UIComponents


def test_session_state_initialization():
    """Test session state initialization."""
    SessionState.initialize()
    assert SessionState.get("view") == "main"
    assert SessionState.get("selected_session") is None
    assert SessionState.get("containers") == {}
    assert SessionState.get("api_healthy") is None

def test_session_state_get_set():
    """Test getting and setting session state values."""
    SessionState.set("test_key", "test_value")
    assert SessionState.get("test_key") == "test_value"
    assert SessionState.get("non_existent") is None

def test_session_state_delete():
    """Test deleting session state values."""
    SessionState.set("test_key", "test_value")
    assert SessionState.get("test_key") == "test_value"
    SessionState.delete("test_key")
    assert SessionState.get("test_key") is None

@pytest.mark.usefixtures("mock_env_vars")
def test_ui_components_render_session_selector(app_test, sample_chat_session):
    """Test rendering the session selector."""
    SessionState.initialize()
    ui = UIComponents()
    
    # Test with no sessions
    ui.render_session_selector([])
    assert "No chat sessions found" in app_test.get_text()
    
    # Test with sessions
    ui.render_session_selector([sample_chat_session])
    assert sample_chat_session["name"] in app_test.get_text()

@pytest.mark.usefixtures("mock_env_vars")
def test_ui_components_render_chat_page(app_test, sample_chat_session):
    """Test rendering the chat page."""
    SessionState.initialize()
    SessionState.set("selected_session", sample_chat_session)
    ui = UIComponents()
    
    ui.render_chat_page()
    
    # Check if messages are displayed
    for message in sample_chat_session["messages"]:
        assert message["content"] in app_test.get_text()

@pytest.mark.usefixtures("mock_env_vars")
def test_callbacks_switch_view():
    """Test view switching callback."""
    SessionState.initialize()
    callbacks = Callbacks()
    
    # Test switching to new chat view
    callbacks.switch_view("new_chat")
    assert SessionState.get("view") == "new_chat"
    
    # Test switching back to main view
    callbacks.switch_view("main")
    assert SessionState.get("view") == "main"

@pytest.mark.usefixtures("mock_env_vars")
def test_callbacks_select_session(sample_chat_session):
    """Test session selection callback."""
    SessionState.initialize()
    callbacks = Callbacks()
    
    callbacks.select_session(sample_chat_session)
    assert SessionState.get("selected_session") == sample_chat_session
    assert SessionState.get("view") == "main"

@pytest.mark.usefixtures("mock_env_vars")
def test_callbacks_refresh_sessions():
    """Test session refresh callback."""
    SessionState.initialize()
    callbacks = Callbacks()
    
    # Test refreshing sessions
    callbacks.refresh_sessions()
    assert SessionState.get("sessions_refreshed") is True

@pytest.mark.usefixtures("mock_env_vars")
def test_callbacks_confirm_delete_session(sample_chat_session):
    """Test session deletion confirmation callback."""
    SessionState.initialize()
    SessionState.set("selected_session", sample_chat_session)
    callbacks = Callbacks()
    
    # Test confirming session deletion
    callbacks.confirm_delete_session()
    assert SessionState.get("selected_session") is None
    assert SessionState.get("view") == "main" 