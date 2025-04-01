"""
Frontend package for the Document Chat application.

This package contains all the frontend components and utilities for the Streamlit-based
chat interface that allows users to interact with their documents using various LLM providers.

Modules:
    - main: Main application entry point
    - components: UI components and session state management
    - forms: Form components and handlers
    - api: API client with caching and retry logic
    - response_analyzer: Response analysis and visualization
    - utils: Utility functions
    - config: Configuration and constants
"""

from app.frontend.api import APIClient
from app.frontend.callbacks import Callbacks
from app.frontend.components import UIComponents
from app.frontend.config import (
    API_BASE_URL,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    API_TIMEOUT,
    CACHE_MAX_ENTRIES,
    CACHE_TTL,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    ERROR_MESSAGES,
    ICONS,
    LLM_PROVIDERS,
    MAX_DOCUMENTS_PER_SESSION,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS_PER_USER,
    SUCCESS_MESSAGES,
    UI_THEME,
)
from app.frontend.forms import Forms
from app.frontend.main import main
from app.frontend.response_analyzer import ResponseAnalyzer, ResponseType
from app.frontend.state import SessionState
from app.frontend.utils import (
    format_datetime,
    format_duration,
    format_file_size,
    generate_session_name,
    parse_duration,
    truncate_text,
)

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "main",
    "SessionState",
    "UIComponents",
    "Callbacks",
    "Forms",
    "APIClient",
    "ResponseAnalyzer",
    "ResponseType",
    "format_datetime",
    "format_file_size",
    "truncate_text",
    "parse_duration",
    "format_duration",
    "generate_session_name",
    "API_BASE_URL",
    "API_TIMEOUT",
    "API_MAX_RETRIES",
    "API_RETRY_DELAY",
    "CACHE_TTL",
    "CACHE_MAX_ENTRIES",
    "MAX_SESSIONS_PER_USER",
    "MAX_MESSAGES_PER_SESSION",
    "UI_THEME",
    "LLM_PROVIDERS",
    "DEFAULT_LLM_PROVIDER",
    "DEFAULT_LLM_MODEL",
    "ERROR_MESSAGES",
    "SUCCESS_MESSAGES",
    "ICONS"
] 