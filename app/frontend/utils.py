import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def parse_duration(duration_str: str) -> float:
    """Parse duration string (e.g., '1m30s') to seconds."""
    total_seconds = 0
    current_number = ""
    
    for char in duration_str:
        if char.isdigit():
            current_number += char
        elif char == 'h':
            total_seconds += int(current_number or 0) * 3600
            current_number = ""
        elif char == 'm':
            total_seconds += int(current_number or 0) * 60
            current_number = ""
        elif char == 's':
            total_seconds += int(current_number or 0)
            current_number = ""
    
    return total_seconds

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds / 60)
    seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {seconds:.1f}s"
    hours = int(minutes / 60)
    minutes = minutes % 60
    return f"{hours}h {minutes}m {seconds:.1f}s"

def extract_metadata(filename: str) -> Dict[str, Any]:
    """Extract metadata from filename."""
    metadata = {
        "original_filename": filename,
        "extension": os.path.splitext(filename)[1].lower(),
        "created_at": datetime.now().isoformat()
    }
    
    # Add more metadata based on file type
    if metadata["extension"] in [".pdf", ".doc", ".docx"]:
        metadata["type"] = "document"
    elif metadata["extension"] in [".jpg", ".jpeg", ".png", ".gif"]:
        metadata["type"] = "image"
    elif metadata["extension"] in [".mp3", ".wav", ".ogg"]:
        metadata["type"] = "audio"
    elif metadata["extension"] in [".mp4", ".avi", ".mov"]:
        metadata["type"] = "video"
    else:
        metadata["type"] = "other"
    
    return metadata

def generate_session_name(documents: List[Dict[str, Any]]) -> str:
    """Generate a session name based on selected documents."""
    if not documents:
        return f"New Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
    if len(documents) == 1:
        doc = documents[0]
        metadata = doc.get("metadata", {})
        title = (
            metadata.get("title") or
            doc.get("title") or
            doc.get("original_filename") or
            os.path.basename(doc.get("filename", "")) or
            f"Document {doc['id'][:8]}"
        )
        return f"Chat with {title}"
    
    doc_names = [
        doc.get("metadata", {}).get("title") or
        doc.get("title") or
        os.path.basename(doc.get("filename", "")) or
        f"Doc {doc['id'][:8]}"
        for doc in documents[:2]
    ]
    
    if len(documents) > 2:
        return f"Chat with {', '.join(doc_names)} and {len(documents)-2} more"
    return f"Chat with {' and '.join(doc_names)}"

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    raise last_exception
        
        return wrapper
    return decorator 