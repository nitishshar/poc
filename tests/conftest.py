"""Common test fixtures for the Document Chat application."""

import os
import tempfile
from typing import Generator

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app_test() -> AppTest:
    """Create a Streamlit AppTest instance."""
    return AppTest.from_file("app/frontend/chat.py")

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("API_BASE_URL", "http://test-api:8000")
    monkeypatch.setenv("CACHE_TTL", "300")
    monkeypatch.setenv("MAX_CACHE_ENTRIES", "1000")
    monkeypatch.setenv("SESSION_TIMEOUT", "3600")
    monkeypatch.setenv("MAX_SESSIONS", "10")
    monkeypatch.setenv("MAX_MESSAGES", "100")
    monkeypatch.setenv("MAX_DOCUMENT_SIZE", "10485760")  # 10MB
    monkeypatch.setenv("MAX_DOCUMENTS", "5")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "gpt-4")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

@pytest.fixture
def sample_documents(temp_dir: str) -> list[str]:
    """Create sample documents for testing."""
    documents = []
    for i in range(3):
        file_path = os.path.join(temp_dir, f"test_doc_{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"This is test document {i}")
        documents.append(file_path)
    return documents

@pytest.fixture
def sample_chat_session() -> dict:
    """Create a sample chat session for testing."""
    return {
        "id": "test-session-123",
        "name": "Test Session",
        "created_at": "2024-03-14T12:00:00Z",
        "documents": ["doc1.txt", "doc2.txt"],
        "llm_provider": "openai",
        "llm_model": "gpt-4",
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2024-03-14T12:01:00Z"
            },
            {
                "role": "assistant",
                "content": "Hi! How can I help you?",
                "timestamp": "2024-03-14T12:01:01Z"
            }
        ]
    } 