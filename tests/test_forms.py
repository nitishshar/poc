"""Tests for the forms module."""

import pytest
from app.frontend.forms import Forms, LLM_PROVIDERS
from app.frontend.components import SessionState

@pytest.mark.usefixtures("mock_env_vars")
def test_forms_render_new_chat_form(app_test, sample_documents):
    """Test rendering the new chat form."""
    SessionState.initialize()
    forms = Forms()
    
    # Set up form state
    SessionState.set("documents", sample_documents)
    SessionState.set("form_key_prefix", "test")
    
    # Render the form
    forms.render_new_chat_form()
    
    # Check if form elements are present
    form_text = app_test.get_text()
    assert "Select Documents" in form_text
    assert "LLM Provider" in form_text
    assert "Model" in form_text
    assert "Session Name (optional)" in form_text

@pytest.mark.usefixtures("mock_env_vars")
def test_forms_handle_create_session_submit(app_test, sample_documents):
    """Test handling form submission for creating a new chat session."""
    SessionState.initialize()
    forms = Forms()
    
    # Set up form state
    form_key_prefix = "test"
    SessionState.set("form_key_prefix", form_key_prefix)
    SessionState.set(f"{form_key_prefix}_documents", sample_documents)
    SessionState.set(f"{form_key_prefix}_llm_provider", "openai")
    SessionState.set(f"{form_key_prefix}_llm_model", "gpt-4")
    SessionState.set(f"{form_key_prefix}_session_name", "Test Session")
    
    # Test form submission
    forms.handle_create_session_submit()
    
    # Check if form was processed
    assert SessionState.get("view") == "main"
    assert SessionState.get(f"{form_key_prefix}_submitted") is True

@pytest.mark.usefixtures("mock_env_vars")
def test_forms_handle_create_session_submit_no_documents(app_test):
    """Test form submission validation when no documents are selected."""
    SessionState.initialize()
    forms = Forms()
    
    # Set up form state with no documents
    form_key_prefix = "test"
    SessionState.set("form_key_prefix", form_key_prefix)
    SessionState.set(f"{form_key_prefix}_documents", [])
    SessionState.set(f"{form_key_prefix}_llm_provider", "openai")
    SessionState.set(f"{form_key_prefix}_llm_model", "gpt-4")
    
    # Test form submission
    forms.handle_create_session_submit()
    
    # Check if error was shown
    assert "Please select at least one document" in app_test.get_text()
    assert SessionState.get(f"{form_key_prefix}_submitted") is False

@pytest.mark.usefixtures("mock_env_vars")
def test_forms_auto_generate_session_name(sample_documents):
    """Test auto-generation of session name."""
    SessionState.initialize()
    forms = Forms()
    
    # Set up form state without session name
    form_key_prefix = "test"
    SessionState.set("form_key_prefix", form_key_prefix)
    SessionState.set(f"{form_key_prefix}_documents", sample_documents)
    SessionState.set(f"{form_key_prefix}_llm_provider", "openai")
    SessionState.set(f"{form_key_prefix}_llm_model", "gpt-4")
    SessionState.set(f"{form_key_prefix}_session_name", "")
    
    # Test form submission
    forms.handle_create_session_submit()
    
    # Check if session name was auto-generated
    generated_name = SessionState.get(f"{form_key_prefix}_session_name")
    assert generated_name is not None
    assert any(doc in generated_name for doc in sample_documents)

def test_llm_providers_configuration():
    """Test LLM providers configuration."""
    # Check if all required providers are present
    required_providers = {"openai", "google", "anthropic"}
    assert all(provider in LLM_PROVIDERS for provider in required_providers)
    
    # Check if each provider has required fields
    for provider, config in LLM_PROVIDERS.items():
        assert "display_name" in config
        assert "models" in config
        assert len(config["models"]) > 0 