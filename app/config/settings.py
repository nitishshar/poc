import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Document Processing Service"
    
    # Database Settings
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "./chroma_db")
    
    # Document Processing Settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    PROCESSED_DIR: str = os.getenv("PROCESSED_DIR", "./processed")
    
    # Text Chunking Settings
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "500"))
    DEFAULT_CHUNK_OVERLAP: int = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "100"))
    
    # PDF Specific Settings
    PDF_HIGHLIGHT_COLOR: str = os.getenv("PDF_HIGHLIGHT_COLOR", "yellow")
    PDF_HIGHLIGHT_OPACITY: float = float(os.getenv("PDF_HIGHLIGHT_OPACITY", "0.3"))
    
    # OCR Settings
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "eng")
    
    # Table Extraction Settings
    EXTRACT_TABLES: bool = os.getenv("EXTRACT_TABLES", "True").lower() in ("true", "1", "t")
    TABLE_CHUNK_SIZE: int = int(os.getenv("TABLE_CHUNK_SIZE", "100"))
    STORE_TABLES_SEPARATELY: bool = os.getenv("STORE_TABLES_SEPARATELY", "True").lower() in ("true", "1", "t")
    
    # Embedding Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    # Processing Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    # Timeout in seconds
    TIMEOUT: int = int(os.getenv("TIMEOUT", "3600"))
    
    # Streamlit Settings
    STREAMLIT_HOST: str = os.getenv("STREAMLIT_HOST", "localhost")
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    
    # Chat Settings
    PERSIST_DOCUMENTS: bool = os.getenv("PERSIST_DOCUMENTS", "True").lower() in ("true", "1", "t")
    PERSIST_CHAT_SESSIONS: bool = os.getenv("PERSIST_CHAT_SESSIONS", "True").lower() in ("true", "1", "t")
    ENABLE_MULTI_DOCUMENT_CHAT: bool = os.getenv("ENABLE_MULTI_DOCUMENT_CHAT", "True").lower() in ("true", "1", "t")
    CHAT_MODE: str = os.getenv("CHAT_MODE", "completion")  # Options: 'completion' or 'assistant'
    MAX_DOCUMENTS_PER_CHAT: int = int(os.getenv("MAX_DOCUMENTS_PER_CHAT", "5"))
    
    # New LLM Provider Settings
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")  # Options: 'openai', 'gemini', 'claude', etc.
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")  # Default model for the provider
    
    # LLM API Keys (can be overridden with environment variables)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")  # For Gemini
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")  # For Claude
    
    # Streamlit UI Performance Settings
    USE_WEBSOCKET_CHAT: bool = os.getenv("USE_WEBSOCKET_CHAT", "True").lower() in ("true", "1", "t")  # Use WebSockets for real-time chat
    CACHE_DOCUMENT_LIST: bool = os.getenv("CACHE_DOCUMENT_LIST", "True").lower() in ("true", "1", "t")
    DOCUMENT_CACHE_TTL: int = int(os.getenv("DOCUMENT_CACHE_TTL", "30"))  # seconds
    
    model_config = {
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True) 