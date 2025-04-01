"""Tests for the API client module."""

import pytest
import responses

from app.frontend.api import APIClient


@pytest.fixture
def mock_responses():
    """Set up mock responses for API calls."""
    with responses.RequestsMock() as rsps:
        yield rsps

def test_join_url():
    """Test URL joining functionality."""
    assert APIClient.join_url("/health") == "http://localhost:8000/api/health"
    assert APIClient.join_url("chat/sessions") == "http://localhost:8000/api/chat/sessions"

@pytest.mark.usefixtures("mock_env_vars")
def test_check_health(mock_responses):
    """Test API health check."""
    mock_responses.add(
        responses.GET,
        "http://test-api:8000/health",
        json={"status": "ok"},
        status=200,
    )
    assert APIClient.check_health() is True

    mock_responses.reset()
    mock_responses.add(
        responses.GET,
        "http://test-api:8000/health",
        json={"status": "error"},
        status=500,
    )
    assert APIClient.check_health() is False

@pytest.mark.usefixtures("mock_env_vars")
def test_get_chat_sessions(mock_responses):
    """Test retrieving chat sessions."""
    sessions = [
        {"id": "1", "name": "Session 1"},
        {"id": "2", "name": "Session 2"},
    ]
    mock_responses.add(
        responses.GET,
        "http://test-api:8000/chat/sessions",
        json=sessions,
        status=200,
    )
    assert APIClient.get_chat_sessions() == sessions

@pytest.mark.usefixtures("mock_env_vars")
def test_create_chat_session(mock_responses, sample_chat_session):
    """Test creating a chat session."""
    mock_responses.add(
        responses.POST,
        "http://test-api:8000/chat/sessions",
        json=sample_chat_session,
        status=201,
    )
    response = APIClient.create_chat_session(
        name="Test Session",
        documents=["doc1.txt", "doc2.txt"],
        llm_provider="openai",
        llm_model="gpt-4",
    )
    assert response == sample_chat_session

@pytest.mark.usefixtures("mock_env_vars")
def test_delete_chat_session(mock_responses):
    """Test deleting a chat session."""
    session_id = "test-session-123"
    mock_responses.add(
        responses.DELETE,
        f"http://test-api:8000/chat/sessions/{session_id}",
        status=204,
    )
    assert APIClient.delete_chat_session(session_id) is True

    mock_responses.reset()
    mock_responses.add(
        responses.DELETE,
        f"http://test-api:8000/chat/sessions/{session_id}",
        status=404,
    )
    assert APIClient.delete_chat_session(session_id) is False

@pytest.mark.usefixtures("mock_env_vars")
def test_send_message(mock_responses):
    """Test sending a message in a chat session."""
    session_id = "test-session-123"
    message = "Hello, how are you?"
    response_message = {
        "role": "assistant",
        "content": "I'm doing well, thank you!",
        "timestamp": "2024-03-14T12:01:01Z",
    }
    
    mock_responses.add(
        responses.POST,
        f"http://test-api:8000/chat/sessions/{session_id}/messages",
        json=response_message,
        status=200,
    )
    
    response = APIClient.send_message(session_id, message)
    assert response == response_message 