from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from app.frontend.api import APIClient
from app.frontend.callbacks import Callbacks
from app.frontend.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    ERROR_MESSAGES,
    ICONS,
    LLM_PROVIDERS,
    MAX_DOCUMENTS_PER_SESSION,
    SUCCESS_MESSAGES,
)
from app.frontend.state import SessionState
from app.frontend.utils import generate_session_name


class Forms:
    """Handles form-related components and callbacks."""
    
    @staticmethod
    def handle_create_session_submit():
        """Handle new chat session form submission."""
        # Get form values from session state
        key_prefix = st.session_state.get("create_session_key_prefix", "main_create")
        selected_docs = st.session_state.get(f"{key_prefix}_doc_select", [])
        session_name = st.session_state.get(f"{key_prefix}_session_name", "")
        llm_provider = st.session_state.get(f"{key_prefix}_llm_provider", DEFAULT_LLM_PROVIDER)
        llm_model = st.session_state.get(f"{key_prefix}_llm_model", DEFAULT_LLM_MODEL)
        
        # Validate input
        if not selected_docs:
            st.error(ERROR_MESSAGES["document_not_found"])
            return
            
        if len(selected_docs) > MAX_DOCUMENTS_PER_SESSION:
            st.error(ERROR_MESSAGES["document_limit"])
            return
            
        # Auto-generate session name if not provided
        if not session_name:
            session_name = generate_session_name(selected_docs)
        
        # Create chat session
        with st.spinner("Creating chat session..."):
            session_data = APIClient.create_chat_session(
                name=session_name,
                document_ids=selected_docs,
                llm_provider=llm_provider,
                llm_model=llm_model
            )
            
            if session_data:
                st.session_state["current_session_id"] = session_data["id"]
                st.session_state["current_view"] = "main"
                st.session_state["newly_created_session"] = True
                st.toast(SUCCESS_MESSAGES["session_created"], icon=ICONS["success"])
            else:
                st.error(ERROR_MESSAGES["api_error"])
    
    @staticmethod
    def render_new_chat_form():
        """Render the new chat form."""
        # Store key prefix in session state
        key_prefix = "main_create"
        st.session_state["create_session_key_prefix"] = key_prefix
        
        # Fetch documents for selection
        documents = APIClient.get_documents()
        if not documents:
            st.error(ERROR_MESSAGES["document_not_found"])
            return
            
        # Document selection
        st.subheader(f"{ICONS['new']} Create New Chat Session")
        selected_docs = st.multiselect(
            "Select Documents",
            options=documents,
            key=f"{key_prefix}_doc_select",
            help=f"Choose up to {MAX_DOCUMENTS_PER_SESSION} documents to chat about.",
            max_selections=MAX_DOCUMENTS_PER_SESSION
        )
        
        # Session name
        session_name = st.text_input(
            "Session Name (Optional)",
            key=f"{key_prefix}_session_name",
            help="Leave empty to auto-generate a name based on selected documents."
        )
        
        # LLM selection
        col1, col2 = st.columns(2)
        with col1:
            llm_provider = st.selectbox(
                "LLM Provider",
                options=list(LLM_PROVIDERS.keys()),
                format_func=lambda x: LLM_PROVIDERS[x]["name"],
                key=f"{key_prefix}_llm_provider",
                index=list(LLM_PROVIDERS.keys()).index(DEFAULT_LLM_PROVIDER)
            )
        with col2:
            available_models = LLM_PROVIDERS[llm_provider]["models"]
            default_model = LLM_PROVIDERS[llm_provider]["default_model"]
            llm_model = st.selectbox(
                "Model",
                options=available_models,
                key=f"{key_prefix}_llm_model",
                index=available_models.index(default_model)
            )
        
        # Submit button
        st.form_submit_button(
            f"{ICONS['success']} Create Chat Session",
            on_click=Forms.handle_create_session_submit,
            use_container_width=True,
            disabled=not selected_docs
        )
        
        # Cancel button
        if st.button(f"{ICONS['error']} Cancel", key="cancel_create"):
            st.session_state["current_view"] = "main" 