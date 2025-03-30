# Document Processing Service

A scalable, efficient, and future-proof service for real-time document ingestion, processing, and analysis. This service supports multiple document formats, performs semantic parsing, metadata extraction, and generates vector embeddings using ChromaDB.

## Features

- **Multi-format Document Support**: Processes PDF, DOCX, TXT, and CSV formats
- **Semantic Parsing & Metadata Extraction**: Extracts meaningful context and metadata
- **Intelligent Text Chunking**: Divides text into logical chunks while maintaining context
- **Vector Embedding Generation**: Integrates with ChromaDB for high-quality embeddings
- **OCR Integration**: Processes scanned documents and image-based PDFs
- **Table Detection and Extraction**: Identifies and processes tables within documents
- **PDF Section Highlighting**: Highlights sections from which responses are inferred
- **Real-time UI**: Monitors processing status through a Streamlit interface
- **Agentic Capability Ready**: Modular architecture supports future agentic features

## Architecture

The service is built using:
- **FastAPI**: For a high-performance backend with async support
- **Streamlit**: For a responsive and user-friendly frontend
- **ChromaDB**: For vector embedding generation and storage
- **PyTesseract**: For OCR capabilities
- **PyPDF2 & pdfplumber**: For PDF processing

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/document-processing-service.git
cd document-processing-service
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. For OCR functionality, install Tesseract:
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt install tesseract-ocr`
   - Mac: `brew install tesseract`

## Configuration

Edit the configuration files in the `app/config` directory to customize:
- Text chunk size
- Embedding model selection
- Table extraction behavior
- PDF highlighting parameters
- OCR settings

## Usage

1. Start the backend service:
```
uvicorn app.main:app --reload
```

2. Start the Streamlit frontend:
```
streamlit run app/frontend/main.py
```

3. Access the UI at http://localhost:8501
4. Access the API documentation at http://localhost:8000/docs

## API Endpoints

- `POST /api/documents/upload`: Upload a new document for processing
- `GET /api/documents/{document_id}`: Get document processing status
- `GET /api/documents/{document_id}/content`: Get processed content
- `GET /api/documents/{document_id}/embeddings`: Get vector embeddings

## Development

Run tests:
```
pytest
```

## License

MIT 