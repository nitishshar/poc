import os
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns correct service information."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "Document Processing Service"
    assert "version" in response.json()
    assert response.json()["status"] == "online"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_endpoint_validation():
    """Test validation of file types in upload endpoint."""
    # Create a sample text file
    sample_file_path = "sample_test.xyz"
    with open(sample_file_path, "w") as f:
        f.write("Test content")
    
    # Try to upload unsupported file type
    with open(sample_file_path, "rb") as f:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("sample.xyz", f, "text/plain")}
        )
    
    # Clean up
    os.remove(sample_file_path)
    
    # Verify response
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_document_status_endpoint_not_found():
    """Test document status endpoint with non-existent document ID."""
    response = client.get("/api/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


if __name__ == "__main__":
    # Run tests manually
    pytest.main(["-xvs", __file__]) 