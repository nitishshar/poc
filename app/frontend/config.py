import os
from typing import Any, Dict, List, Optional

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1.0"))

# Cache configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "1000"))

# Session configuration
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour
MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "10"))
MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "100"))

# UI configuration
UI_MAX_WIDTH = "1200px"
UI_THEME = {
    "primary": "#FF4B4B",
    "secondary": "#7E7E7E",
    "background": "#FFFFFF",
    "text": "#31333F"
}

# LLM configuration
LLM_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "default_model": "gpt-4"
    },
    "google": {
        "name": "Google Gemini",
        "models": ["gemini-pro"],
        "default_model": "gemini-pro"
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
        "default_model": "claude-3-opus-20240229"
    }
}

DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4")

# Document configuration
SUPPORTED_DOCUMENT_TYPES = {
    "document": [".pdf", ".doc", ".docx", ".txt", ".md"],
    "spreadsheet": [".csv", ".xls", ".xlsx"],
    "presentation": [".ppt", ".pptx"],
    "image": [".jpg", ".jpeg", ".png", ".gif"],
    "code": [".py", ".js", ".java", ".cpp", ".h", ".cs", ".php", ".rb", ".go", ".rs"]
}

MAX_DOCUMENT_SIZE = int(os.getenv("MAX_DOCUMENT_SIZE", str(10 * 1024 * 1024)))  # 10MB
MAX_DOCUMENTS_PER_SESSION = int(os.getenv("MAX_DOCUMENTS_PER_SESSION", "5"))

# Upload settings
MAX_UPLOAD_SIZE_MB = 200  # Maximum file size in MB
SUPPORTED_FORMATS = ["pdf", "txt", "doc", "docx", "csv"]

# Error messages
ERROR_MESSAGES = {
    "api_error": "The API is not responding. Please check if the backend service is running.",
    "session_not_found": "Chat session not found. It might have been deleted.",
    "document_not_found": "Document not found. It might have been deleted.",
    "invalid_document": "Invalid document type or size.",
    "session_limit": f"Maximum number of sessions ({MAX_SESSIONS_PER_USER}) reached.",
    "document_limit": f"Maximum number of documents ({MAX_DOCUMENTS_PER_SESSION}) per session reached.",
    "message_limit": f"Maximum number of messages ({MAX_MESSAGES_PER_SESSION}) per session reached."
}

# Success messages
SUCCESS_MESSAGES = {
    "session_created": "Chat session created successfully!",
    "session_deleted": "Chat session deleted successfully!",
    "message_sent": "Message sent successfully!",
    "document_uploaded": "Document uploaded successfully!",
    "state_reset": "Session state reset successfully!"
}

# Icons
ICONS = {
    "app": "📚",
    "chat": "💬",
    "document": "📄",
    "success": "✨",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "delete": "🗑️",
    "refresh": "🔄",
    "new": "➕",
    "settings": "⚙️",
    "upload": "📤",
    "download": "📥",
    "search": "🔍",
    "user": "👤",
    "assistant": "🤖"
} 