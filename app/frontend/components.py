import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from app.frontend.api import APIClient
from app.frontend.config import (
    ERROR_MESSAGES,
    ICONS,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_USER,
    MAX_UPLOAD_SIZE_MB,
    SUCCESS_MESSAGES,
    UI_THEME,
)
from app.frontend.forms import Forms
from app.frontend.response_analyzer import ResponseAnalyzer, ResponseType
from app.frontend.state import SessionState
from app.frontend.upload import UploadManager
from app.frontend.utils import format_datetime, format_file_size, truncate_text


class UIComponents:
    """Contains all UI rendering functions with proper caching."""
    
    @staticmethod
    @st.cache_data(ttl=300)
    def format_datetime(dt_str: str) -> str:
        """Format datetime string with caching."""
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return dt_str

    @staticmethod
    def render_session_selector():
        """Render the session selection UI."""
        sessions = SessionState.get("chat_sessions", [])
        if not sessions:
            sessions = APIClient.get_chat_sessions()
            if sessions:
                try:
                    sessions.sort(key=lambda s: datetime.fromisoformat(
                        s.get('updated_at', '1970-01-01T00:00:00+00:00').replace('Z', '+00:00')
                    ), reverse=True)
                except Exception as e:
                    print(f"Error sorting sessions: {e}")
                SessionState.set("chat_sessions", sessions)
            else:
                SessionState.set("chat_sessions", [])

        current_session_id = SessionState.get("current_session_id")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            if sessions:
                if len(sessions) >= MAX_SESSIONS_PER_USER:
                    st.warning(ERROR_MESSAGES["session_limit"])
                
                session_options = {
                    s["id"]: f"{s.get('name', 'Unnamed')} ({format_datetime(s.get('updated_at', ''))})"
                    for s in sessions
                }
                display_options = {"": "--- Select a Session ---"} | session_options
                options_keys = list(display_options.keys())
                current_index = options_keys.index(current_session_id) if current_session_id in options_keys else 0
                
                st.selectbox(
                    "Select Chat Session",
                    options=options_keys,
                    format_func=lambda x: display_options.get(x, x),
                    key="session_selector_widget",
                    index=current_index,
                    on_change=Callbacks.select_session,
                    label_visibility="collapsed"
                )
            else:
                st.info("No chat sessions.")
        
        with col2:
            st.button(
                f"{ICONS['new']} New Chat",
                key="new_chat_btn",
                on_click=Callbacks.switch_view,
                args=("new_chat",),
                use_container_width=True,
                disabled=len(sessions) >= MAX_SESSIONS_PER_USER
            )
        
        with col3:
            st.button(
                f"{ICONS['refresh']} Refresh",
                key="refresh_btn",
                on_click=Callbacks.refresh_sessions,
                use_container_width=True
            )

    @staticmethod
    def render_message(message: Dict[str, Any]):
        """Render a single message with appropriate visualization."""
        with st.chat_message(
            message["role"],
            avatar=ICONS.get(message["role"], ICONS["user"])
        ):
            text = message["text"]
            response_type = ResponseAnalyzer.analyze_response(text)
            
            if response_type == ResponseType.TABLE:
                table_data = ResponseAnalyzer.parse_table(text)
                if table_data:
                    st.table(table_data)
                else:
                    st.markdown(text)
                    
            elif response_type == ResponseType.LIST:
                items = ResponseAnalyzer.parse_list(text)
                if items:
                    for item in items:
                        st.markdown(f"- {item}")
                else:
                    st.markdown(text)
                    
            elif response_type == ResponseType.CHART:
                chart_data = ResponseAnalyzer.parse_chart_data(text)
                if chart_data["data"]:
                    st.line_chart(chart_data["data"])
                else:
                    st.markdown(text)
                    
            else:
                st.markdown(text)

    @staticmethod
    def render_chat_page():
        """Render the main chat interface."""
        st.title("💬 Chat Sessions")
        
        # Add custom CSS for a more professional, compact design
        st.markdown("""
        <style>
        /* Compact card-like design for sessions */
        div.session-card {
            background-color: #1E1E2E;
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 8px;
            border: 1px solid #2A2A3A;
            transition: all 0.3s;
        }
        div.session-card:hover {
            border-color: #4A4A5A;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        /* Session title styling */
        .session-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0;
            padding: 0;
        }
        
        /* Session date styling */
        .session-date {
            font-size: 12px;
            color: #999;
            margin: 3px 0 0 0;
        }
        
        /* Make buttons more compact */
        .stButton>button {
            padding: 2px 8px;
            height: 32px;
            min-height: 32px;
            font-size: 12px;
        }
        
        /* Reduce spacing between elements */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        
        .element-container {
            margin-bottom: 8px;
        }
        
        /* Session card grid layout */
        .session-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 10px;
        }
        
        /* Compact session cards */
        .compact-card {
            margin-bottom: 10px;
        }
        
        /* Smaller header margins */
        h1, h2, h3 {
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Command bar - single row with all actions
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button("➕ New Chat", key="new_chat_btn", use_container_width=True, type="primary"):
                SessionState.set("current_view", "new_chat")
                st.rerun()
        with col2:
            if st.button("🔄 Refresh", key="refresh_chats", use_container_width=True):
                st.cache_data.clear()
                try:
                    APIClient.get_chat_sessions.clear()
                except:
                    pass
                st.rerun()
        
        # Try to fetch sessions with cache cleared
        with st.spinner("Loading chat sessions..."):
            try:
                st.cache_data.clear()
                try:
                    APIClient.get_chat_sessions.clear()
                except:
                    pass
                sessions = APIClient.get_chat_sessions()
            except Exception as e:
                st.error(f"Error loading chat sessions: {str(e)}")
                sessions = []
        
        # Display a message if no sessions are found
        if not sessions:
            st.info("No chat sessions found. Create a new chat to get started!")
            return

        # Display sessions in a more compact layout
        st.markdown("<div class='session-grid'>", unsafe_allow_html=True)
        
        for i, session in enumerate(sessions):
            session_id = session.get("id", "")
            session_name = session.get("name", "Unnamed Session")
            
            # Use HTML for more compact session cards
            st.markdown(f"""
            <div class='compact-card'>
                <div class="session-card">
                    <p class="session-title">{session_name}</p>
                    <p class="session-date">Created: {format_datetime(session.get('created_at', ''))}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Compact action buttons in a row
            b_col1, b_col2, b_col3 = st.columns(3)
            with b_col1:
                if st.button("Open", key=f"open_{session_id}", use_container_width=True):
                    SessionState.set("active_session", session_id)
                    SessionState.set("active_session_name", session_name)
                    st.rerun()
            with b_col2:
                if st.button("Rename", key=f"rename_{session_id}", use_container_width=True):
                    SessionState.set("renaming_session", session_id)
                    SessionState.set("renaming_session_name", session_name)
                    st.rerun()
            with b_col3:
                if st.button("Delete", key=f"delete_{session_id}", use_container_width=True, type="secondary"):
                    result = APIClient.delete_chat_session(session_id)
                    if result:
                        st.success(f"Session deleted successfully")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to delete session")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Handle active session (view chat)
        active_session_id = SessionState.get("active_session")
        active_session_name = SessionState.get("active_session_name")
        
        if active_session_id:
            st.markdown("---")
            st.markdown(f"### Chat: {active_session_name}")
            
            # Get session messages
            session_data = APIClient.get_chat_session(active_session_id)
            
            if session_data:
                # Display messages
                messages = session_data.get("messages", [])
                if not messages:
                    st.info("No messages in this chat session. Start typing below!")
                else:
                    for message in messages:
                        UIComponents.render_message(message)
                
                # Chat input in a cleaner form
                with st.form(key="session_chat_form", clear_on_submit=True):
                    message = st.text_area(
                        "Your Message",
                        key=f"message_input_{active_session_id}",
                        placeholder="Type your message here...",
                        height=80
                    )
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        submitted = st.form_submit_button("Send", use_container_width=True, type="primary")
                    with col2:
                        if st.form_submit_button("Close Chat", use_container_width=True):
                            SessionState.delete("active_session")
                            SessionState.delete("active_session_name")
                            st.rerun()
                    
                    if submitted and message:
                        with st.spinner("Sending message..."):
                            response = APIClient.send_message(active_session_id, message)
                            if response:
                                st.rerun()
                            else:
                                st.error("Failed to send message.")
            else:
                st.error("Failed to load chat session.")
        
        # Handle renaming session - more compact form
        renaming_session_id = SessionState.get("renaming_session")
        renaming_session_name = SessionState.get("renaming_session_name")
        
        if renaming_session_id:
            st.markdown("---")
            with st.form(key="rename_session_form"):
                st.subheader(f"Rename Session")
                new_name = st.text_input("New Name", value=renaming_session_name)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("Save", use_container_width=True, type="primary"):
                        # Call the rename API method
                        result = APIClient.rename_chat_session(renaming_session_id, new_name)
                        if result:
                            st.success(f"Session renamed to '{new_name}'.")
                            # Clear cache and refresh list
                            st.cache_data.clear()
                            try:
                                APIClient.get_chat_sessions.clear()
                            except:
                                pass
                        else:
                            st.error(f"Failed to rename session to '{new_name}'.")
                        
                        # Close the rename form
                        SessionState.delete("renaming_session")
                        SessionState.delete("renaming_session_name")
                        time.sleep(0.5)
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        SessionState.delete("renaming_session")
                        SessionState.delete("renaming_session_name")
                        st.rerun()

    @staticmethod
    def render_new_chat_form():
        """Render the new chat form."""
        return Forms.render_new_chat_form()

    @staticmethod
    def render_upload_page():
        """Render the document upload interface."""
        return UploadManager.render_upload_page()

    @staticmethod
    def render_document_manager():
        """Render the document manager interface."""
        st.title("📄 Document Manager")
        
        # Document list
        st.subheader("Your Documents")
        
        # Add a container for the progress spinner and status
        progress_container = st.empty()
        
        # Handle potential None response from API safely
        try:
            documents = APIClient.get_documents()
            if documents is None:
                documents = []  # Ensure documents is a list even if API returns None
        except Exception as e:
            st.error(f"Error fetching documents: {str(e)}")
            documents = []
        
        # Check for processing documents
        processing_docs = [doc for doc in documents if doc.get("status") == "processing"]
        if processing_docs:
            with progress_container.container():
                st.info(f"{len(processing_docs)} documents are being processed")
                progress_bar = st.progress(0)
                
                # Add auto-refresh for processing documents
                if not st.session_state.get('processing_complete', False):
                    with st.spinner("Processing documents..."):
                        # Display each processing document
                        for doc in processing_docs:
                            doc_name = doc.get("original_filename", "Unnamed document")
                            doc_status = doc.get("status", "Unknown")
                            doc_progress = doc.get("processing_progress", 0)
                            
                            # Handle potential None or invalid progress values
                            try:
                                progress_value = float(doc_progress) / 100 if doc_progress is not None else 0
                                progress_value = max(0, min(1, progress_value))  # Clamp between 0 and 1
                            except (ValueError, TypeError):
                                progress_value = 0
                                
                            st.text(f"Processing: {doc_name} - {doc_status} ({int(progress_value * 100)}%)")
                            
                        # Set overall progress to average of all documents
                        overall_progress = sum(float(doc.get("processing_progress", 0) or 0) for doc in processing_docs) / len(processing_docs) / 100
                        progress_bar.progress(overall_progress)
                        
                        # Auto-refresh every 3 seconds if documents are still processing
                        if overall_progress < 1.0:
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.session_state['processing_complete'] = True
                            st.success("All documents processed successfully!")
        
        if not documents:
            st.info("No documents found. Upload some documents to get started!")
            # Navigation buttons for empty state
            if st.button("📤 Upload Documents", key="upload_empty", use_container_width=True):
                SessionState.set("current_view", "upload")
                st.rerun()
            return
            
        # Create a dataframe for better display
        docs_data = []
        for doc in documents:
            # Extract metadata properly with better fallbacks
            metadata = doc.get("metadata", {}) or {}
            
            # Get file size - check multiple possible locations
            file_size = metadata.get("size", 0)
            if not file_size and "file_size" in doc:
                file_size = doc.get("file_size", 0)
            
            # Get processing status - map status to human-readable format
            doc_status = doc.get("status", "Unknown")
            
            # Get processing steps to determine detailed status
            processing_steps = doc.get("processing_steps", [])
            processing_progress = doc.get("processing_progress", 0)
            if not processing_progress and processing_steps:
                # Calculate progress from steps if available
                completed_steps = sum(1 for step in processing_steps if step.get("status") == "completed")
                total_steps = len(processing_steps)
                processing_progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0
            
            # Determine processing status from steps
            if processing_steps:
                # Find the current processing step
                current_step = next((step for step in processing_steps if step.get("status") == "processing"), None)
                if current_step:
                    processing_status = f"Step: {current_step.get('name', 'Unknown')} ({int(processing_progress)}%)"
                elif doc_status == "processed":
                    processing_status = "Completed (100%)"
                elif doc_status == "failed":
                    processing_status = "Failed"
                else:
                    processing_status = f"{doc_status.title()} ({int(processing_progress)}%)"
            else:
                # Fallback if no steps are available
                if doc_status == "processed":
                    processing_status = "Completed"
                elif doc_status == "processing":
                    processing_status = f"Processing ({int(processing_progress)}%)"
                elif doc_status == "failed":
                    processing_status = "Failed"
                else:
                    processing_status = doc.get("processing_status", doc_status.title())
            
            # Get embedding status
            embedding_status = doc.get("embedding_status", "Not Started")
            if embedding_status == "completed":
                embedding_status = "Completed"
            elif embedding_status == "processing":
                embedding_progress = doc.get("embedding_progress", 0)
                embedding_status = f"Processing ({int(embedding_progress)}%)"
            
            # Get timestamps and ensure they're not None
            created_at = doc.get("created_at", "")
            updated_at = doc.get("updated_at", "")
            
            # Add document data to the list with safe values
            docs_data.append({
                "Name": doc.get("original_filename", "Unnamed") or "Unnamed",
                "Type": metadata.get("mime_type", metadata.get("type", "Unknown")) or "Unknown",
                "Size": format_file_size(file_size),
                "Status": doc_status.title(),
                "Processing": processing_status,
                "Embedding": embedding_status,
                "Created": format_datetime(created_at),
                "Updated": format_datetime(updated_at),
                "Actions": doc.get("id", ""),
                # Store the full document object for viewing
                "FullDocument": doc  
            })
        
        # Display document table with filtering and sorting
        df = pd.DataFrame(docs_data)
        
        # Add column configurations for better display
        st.dataframe(
            df.drop(columns=["FullDocument"]),  # Don't show the full document in the table
            column_config={
                "Actions": st.column_config.Column(
                    "Actions",
                    help="Document actions",
                    width="small"
                ),
                "Status": st.column_config.Column(
                    "Status",
                    help="Document status",
                    width="medium"
                ),
                "Processing": st.column_config.Column(
                    "Processing",
                    help="Document processing progress",
                    width="medium"
                ),
                "Embedding": st.column_config.Column(
                    "Embedding",
                    help="Embedding generation progress",
                    width="medium"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Add action buttons below the table
        if len(docs_data) > 0:
            st.subheader("Document Actions")
            for doc in docs_data:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"**{doc['Name']}**")
                with col2:
                    if st.button(
                        "View",
                        key=f"view_{doc['Actions']}",
                        use_container_width=True,
                    ):
                        # Store the full document object for viewing
                        SessionState.set("viewing_document", doc["FullDocument"])
                        st.rerun()
                with col3:
                    if st.button(
                        "Delete",
                        key=f"delete_{doc['Actions']}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        try:
                            APIClient.delete_document(doc['Actions'])
                            st.success(f"Document {doc['Name']} deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting document: {str(e)}")
                with col4:
                    if st.button(
                        "Reprocess",
                        key=f"reprocess_{doc['Actions']}",
                        use_container_width=True,
                        type="primary"
                    ):
                        try:
                            # Reset processing state on reprocess
                            st.session_state['processing_complete'] = False
                            APIClient.reprocess_document(doc['Actions'])
                            st.success(f"Document {doc['Name']} queued for reprocessing")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error reprocessing document: {str(e)}")
        
        # Document viewer
        viewing_doc = SessionState.get("viewing_document")
        if viewing_doc:
            with st.expander(f"Viewing: {viewing_doc.get('original_filename', 'Unnamed Document')}", expanded=True):
                # Display document metadata in a more readable format
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Document Information")
                    st.markdown(f"**Document ID:** `{viewing_doc.get('id', 'Unknown')}`")
                    st.markdown(f"**Filename:** {viewing_doc.get('original_filename', 'Unknown')}")
                    st.markdown(f"**Size:** {format_file_size(viewing_doc.get('file_size', 0))}")
                    st.markdown(f"**Type:** {viewing_doc.get('file_type', 'Unknown')}")
                    st.markdown(f"**Created:** {format_datetime(viewing_doc.get('created_at', ''))}")
                    st.markdown(f"**Updated:** {format_datetime(viewing_doc.get('updated_at', ''))}")
                
                with col2:
                    st.markdown("### Processing Information")
                    st.markdown(f"**Status:** {viewing_doc.get('status', 'Unknown').title()}")
                    st.markdown(f"**Processing Progress:** {viewing_doc.get('processing_progress', 0)}%")
                    
                    # Display embedding information
                    embedding_status = viewing_doc.get('embedding_status', 'Not Started')
                    embedding_progress = viewing_doc.get('embedding_progress', 0)
                    st.markdown(f"**Embedding Status:** {embedding_status.title()}")
                    st.markdown(f"**Embedding Progress:** {embedding_progress}%")
                    
                    # Show any errors if present
                    if error := viewing_doc.get('error'):
                        st.error(f"**Error:** {error}")
                
                # Show processing steps if available
                processing_steps = viewing_doc.get('processing_steps', [])
                if processing_steps:
                    st.markdown("### Processing Steps")
                    for i, step in enumerate(processing_steps):
                        step_status = step.get('status', 'unknown')
                        step_icon = "✅" if step_status == "completed" else "⏳" if step_status == "processing" else "❌" if step_status == "failed" else "⏸️"
                        st.markdown(f"{step_icon} **Step {i+1}: {step.get('name', 'Unknown')}** - {step_status.title()}")
                        if step.get('error'):
                            st.error(f"Error: {step.get('error')}")
                
                # Show raw JSON for debugging - without using an expander to avoid nesting error
                st.markdown("### Raw JSON Data")
                show_json = st.checkbox("Show raw JSON data", key="show_raw_json")
                if show_json:
                    st.json(viewing_doc)
                
                if st.button("Close", key="close_viewer"):
                    SessionState.delete("viewing_document")
                    st.rerun()

        # Navigation and refresh buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Upload Documents", use_container_width=True):
                SessionState.set("current_view", "upload")
                st.rerun()
        with col2:
            if st.button("🔄 Refresh List", use_container_width=True):
                # Reset processing state on refresh
                st.session_state['processing_complete'] = False
                # Clear all related caches
                st.cache_data.clear()
                try:
                    # Try all possible cache clear methods to ensure fresh data
                    if hasattr(APIClient.get_documents, 'clear'):
                        APIClient.get_documents.clear()
                    if hasattr(APIClient.get_documents, 'cache_clear'):
                        APIClient.get_documents.cache_clear()
                except Exception as e:
                    st.error(f"Error clearing cache: {str(e)}")
                # Force a rerun to fetch fresh data
                st.rerun()

    @staticmethod
    def render_search_page():
        """Render the search and embeddings interface."""
        st.title("🔍 Search & Embeddings")
        
        # Search section
        st.subheader("Semantic Search")
        with st.form(key="search_form"):
            query = st.text_area(
                "Search Query",
                placeholder="Enter your search query...",
                help="Use natural language to search across your documents"
            )
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                # Get documents with cache cleared
                try:
                    st.cache_data.clear()
                    documents = APIClient.get_documents()
                except:
                    documents = []
                
                selected_docs = st.multiselect(
                    "Search in Documents",
                    options=documents,
                    format_func=lambda x: x.get("original_filename", "Unnamed"),
                    help="Select documents to search in (optional)"
                )
            with col2:
                top_k = st.number_input(
                    "Top K Results",
                    min_value=1,
                    max_value=100,
                    value=10
                )
            with col3:
                threshold = st.slider(
                    "Similarity Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.7,
                    step=0.1
                )
            
            submitted = st.form_submit_button(
                "Search",
                type="primary",
                use_container_width=True
            )
            
            if submitted and query:
                with st.spinner("Searching..."):
                    # Get selected document IDs
                    doc_ids = [doc.get("id") for doc in selected_docs] if selected_docs else None
                    
                    # Perform the search
                    search_results = APIClient.semantic_search(
                        query=query,
                        doc_ids=doc_ids,
                        top_k=top_k,
                        threshold=threshold
                    )
                    
                    if search_results.get("success"):
                        results = search_results.get("data", {}).get("results", [])
                        
                        if results:
                            st.success(f"Found {len(results)} results")
                            
                            # Display search results
                            for i, result in enumerate(results):
                                with st.container():
                                    col1, col2 = st.columns([4, 1])
                                    with col1:
                                        st.markdown(f"### {i+1}. {result.get('document_name', 'Unknown document')}")
                                        st.markdown(f"**Score:** {result.get('score', 0):.2f}")
                                        st.markdown(f"**Chunk:** {result.get('chunk_id', 'Unknown chunk')}")
                                        st.markdown(f"**Text:**")
                                        st.markdown(f"> {result.get('text', 'No text available')}")
                                    with col2:
                                        if st.button("View Document", key=f"view_result_{i}"):
                                            # Get document details and view it
                                            doc_id = result.get("document_id")
                                            if doc_id:
                                                # Redirect to document viewer
                                                pass
                        else:
                            st.warning("No results found matching your query.")
                    else:
                        st.error(f"Search failed: {search_results.get('error', 'Unknown error')}")
        
        # Embeddings section
        st.subheader("Document Embeddings")
        with st.expander("Manage Embeddings", expanded=True):
            # Clear cache to get fresh data
            try:
                st.cache_data.clear()
                documents = APIClient.get_documents()
            except:
                documents = []
                
            if not documents:
                st.info("No documents found.")
                return
            
            # Add a button to refresh embedding status
            if st.button("🔄 Refresh Embedding Status", key="refresh_embeddings"):
                st.cache_data.clear()
                try:
                    APIClient.get_documents.clear()
                except:
                    pass
                st.rerun()
                
            for doc in documents:
                col1, col2 = st.columns([3, 1])
                with col1:
                    doc_name = doc.get("original_filename", "Unnamed")
                    st.write(f"**{doc_name}**")
                    
                    # Get embedding status
                    embedding_status = doc.get("embedding_status", "not_started")
                    if embedding_status == "completed":
                        st.success("✅ Embedded")
                    elif embedding_status == "processing":
                        progress = doc.get("embedding_progress", 0)
                        st.info(f"⏳ Embedding in progress ({progress}%)")
                    elif embedding_status == "failed":
                        st.error("❌ Embedding failed")
                    else:
                        st.warning("⏸️ Not embedded")
                with col2:
                    doc_id = doc.get("id")
                    if doc_id:
                        if embedding_status not in ["completed", "processing"]:
                            if st.button(
                                "Generate Embeddings",
                                key=f"embed_{doc_id}",
                                use_container_width=True
                            ):
                                with st.spinner(f"Generating embeddings for {doc_name}..."):
                                    result = APIClient.generate_embeddings(doc_id)
                                    if result.get("success"):
                                        st.success(f"Started embedding generation for {doc_name}")
                                        time.sleep(1)  # Short delay to show the message
                                        st.rerun()  # Refresh to show updated status
                                    else:
                                        st.error(f"Failed to generate embeddings: {result.get('error', 'Unknown error')}")
                        elif embedding_status == "completed":
                            if st.button(
                                "Regenerate",
                                key=f"reembed_{doc_id}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                with st.spinner(f"Regenerating embeddings for {doc_name}..."):
                                    result = APIClient.generate_embeddings(doc_id)
                                    if result.get("success"):
                                        st.success(f"Started embedding regeneration for {doc_name}")
                                        time.sleep(1)  # Short delay to show the message
                                        st.rerun()  # Refresh to show updated status
                                    else:
                                        st.error(f"Failed to regenerate embeddings: {result.get('error', 'Unknown error')}")
                        elif embedding_status == "processing":
                            st.button(
                                "Processing...",
                                key=f"processing_{doc_id}",
                                use_container_width=True,
                                disabled=True
                            )
                    else:
                        st.button(
                            "No Document ID",
                            key=f"no_id_{doc.get('original_filename', 'doc')}",
                            use_container_width=True,
                            disabled=True
                        )

    @staticmethod
    def render_document_status():
        """Render the document status interface."""
        st.title("📊 Document Status")
        
        documents = APIClient.get_documents()
        if not documents:
            st.info("No documents found.")
            return
        
        # Overall stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_docs = len(documents)
            st.metric("Total Documents", total_docs)
        
        with col2:
            processed_docs = sum(1 for d in documents if d.get("status") == "processed")
            st.metric("Processed", processed_docs)
        
        with col3:
            embedded_docs = sum(1 for d in documents if d.get("embedding_status") == "completed")
            st.metric("Embedded", embedded_docs)
        
        with col4:
            failed_docs = sum(1 for d in documents if d.get("status") == "failed")
            st.metric("Failed", failed_docs)
        
        # Status table
        st.subheader("Document Processing Status")
        
        status_data = []
        for doc in documents:
            status_data.append({
                "Name": doc.get("original_filename", "Unnamed"),
                "Processing Status": doc.get("status", "Unknown"),
                "Embedding Status": doc.get("embedding_status", "Not started"),
                "Error": doc.get("error", ""),
                "Last Updated": format_datetime(doc.get("updated_at", "")),
                "Actions": doc.get("id", "")
            })
        
        df = pd.DataFrame(status_data)
        st.dataframe(
            df,
            column_config={
                "Name": st.column_config.Column(
                    "Name",
                    help="Document name",
                    width="large"
                ),
                "Processing Status": st.column_config.Column(
                    "Processing Status",
                    help="Current processing status",
                    width="medium"
                ),
                "Embedding Status": st.column_config.Column(
                    "Embedding Status",
                    help="Current embedding status",
                    width="medium"
                ),
                "Error": st.column_config.Column(
                    "Error",
                    help="Error message if any",
                    width="large"
                ),
                "Last Updated": st.column_config.Column(
                    "Last Updated",
                    help="Last update time",
                    width="medium"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Add action buttons below the table
        if len(status_data) > 0:
            st.subheader("Status Actions")
            for doc in status_data:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{doc['Name']}**")
                with col2:
                    st.button(
                        "Retry Processing",
                        key=f"retry_{doc['Actions']}",
                        use_container_width=True,
                        type="primary",
                        disabled=doc['Processing Status'] == "Processing"
                    )
                with col3:
                    st.button(
                        "Clear Error",
                        key=f"clear_{doc['Actions']}",
                        use_container_width=True,
                        type="secondary",
                        disabled=not doc['Error']
                    )
        
        # Refresh button
        st.button(
            "🔄 Refresh Status",
            use_container_width=True,
            type="primary"
        )

class Callbacks:
    """Contains all callback functions for UI interactions."""
    
    @staticmethod
    def switch_view(view_name: str):
        """Switch the current view."""
        SessionState.set("current_view", view_name)
        SessionState.set("confirm_delete", False)

    @staticmethod
    def select_session():
        """Handle session selection."""
        selected_id = SessionState.get("session_selector_widget")
        if selected_id and selected_id != SessionState.get("current_session_id"):
            SessionState.set("current_session_id", selected_id)
            SessionState.delete("current_session_cache")
            SessionState.set("confirm_delete", False)

    @staticmethod
    def refresh_sessions():
        """Refresh the session list."""
        APIClient.get_chat_sessions.cache_clear()
        SessionState.set("chat_sessions", [])
        st.toast(SUCCESS_MESSAGES["state_reset"], icon=ICONS["refresh"])

    @staticmethod
    def handle_delete_session():
        """Handle session deletion request."""
        SessionState.set("confirm_delete", True)

    @staticmethod
    def confirm_delete_session():
        """Confirm and execute session deletion."""
        current_session_id = SessionState.get("current_session_id")
        if not current_session_id:
            return
            
        if APIClient.delete_chat_session(current_session_id):
            st.toast(SUCCESS_MESSAGES["session_deleted"], icon=ICONS["success"])
            SessionState.set("deletion_succeeded", True)
            SessionState.set("current_session_id", None)
            SessionState.delete("current_session_cache")
        else:
            st.error(ERROR_MESSAGES["session_not_found"])
            
        SessionState.set("confirm_delete", False)

    @staticmethod
    def cancel_delete_session():
        """Cancel session deletion."""
        SessionState.set("confirm_delete", False)

    @staticmethod
    def handle_send_message():
        """Handle sending a message."""
        user_input = SessionState.get("message_input")
        current_session_id = SessionState.get("current_session_id")
        
        if not user_input or not current_session_id:
            return
            
        with st.spinner("Sending message..."):
            response_data = APIClient.send_message(current_session_id, user_input)
            if response_data:
                SessionState.set("current_session_cache", response_data)
                st.toast(SUCCESS_MESSAGES["message_sent"], icon=ICONS["send"])
            else:
                st.error(ERROR_MESSAGES["session_not_found"]) 