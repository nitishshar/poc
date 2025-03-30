# Document Processing Service - Developer Manual

This manual provides instructions for setting up and running the Document Processing Service application for development purposes.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Setting Up the Development Environment](#setting-up-the-development-environment)
3. [Installing Dependencies](#installing-dependencies)
4. [Application Configuration](#application-configuration)
5. [Running the Application](#running-the-application)
6. [Development Workflow](#development-workflow)
7. [Troubleshooting](#troubleshooting)

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: At least 4GB RAM (8GB recommended for processing large documents)
- **Storage**: Minimum 1GB free space
- **Additional Software**:
  - Tesseract OCR (for OCR functionality)
  - Poppler (for PDF processing)

## Setting Up the Development Environment

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd document-processing-service
```

### Step 2: Create a Python Virtual Environment

Python's built-in venv module provides a lightweight approach for environment management.

#### For Windows:

```bash
# Create a new virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```

#### For macOS/Linux:

```bash
# Create a new virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### Step 3: Install System Dependencies

#### For Windows:

1. Install Tesseract OCR:
   - Download the installer from [UB Mannheim's GitHub repository](https://github.com/UB-Mannheim/tesseract/wiki)
   - Add Tesseract to your PATH (usually `C:\Program Files\Tesseract-OCR`)

2. Install Poppler:
   - Download the latest version from [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - Extract the files and add the `bin` directory to your PATH

#### For macOS:

```bash
# Using Homebrew
brew install tesseract
brew install poppler
```

#### For Linux (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
sudo apt-get install -y poppler-utils
```

## Installing Dependencies

### Option 1: Standard Installation

While in your activated virtual environment, install the required Python packages:

```bash
# Install all dependencies at once
pip install -r requirements.txt
```

### Option 2: Staged Installation (Recommended for Troubleshooting)

If you encounter issues with the standard installation, try installing critical packages first:

```bash
# Install critical packages first
pip install sentence-transformers
pip install chromadb

# Then install remaining packages
pip install -r requirements.txt
```

### Option 3: Resolving Dependency Conflicts

If you encounter dependency conflicts between packages (especially with pydantic versions or sentence-transformers), it's best to start with a clean environment and install dependencies in the correct order:

```bash
# Exit current environment if active
deactivate

# Create a fresh environment
python -m venv fresh_venv

# Activate the new environment
fresh_venv\Scripts\activate  # On Windows
# OR
source fresh_venv/bin/activate  # On macOS/Linux

# Install in correct order with compatible versions
pip install huggingface-hub==0.16.4
pip install transformers==4.30.2
pip install sentence-transformers==2.2.2
pip install chromadb>=0.4.18,<0.5.0

# Install other core packages
pip install "pydantic>=2.7.0,<3.0.0"
pip install "pydantic-settings>=2.8.1,<3.0.0"
pip install "fastapi>=0.104.1,<0.105.0"
pip install uvicorn>=0.23.2,<0.24.0 streamlit>=1.28.0,<1.29.0

# Install remaining dependencies
pip install python-multipart asyncio
pip install PyPDF2 pdfplumber python-docx pandas openpyxl
pip install pytesseract Pillow
pip install tqdm python-dotenv loguru pytest httpx
```

This will install all necessary Python libraries including:
- FastAPI
- Streamlit
- ChromaDB
- PyMuPDF
- Pandas
- Sentence Transformers
- Pytesseract
- And other required packages

### Dealing with OpenMP Issues

If you encounter OpenMP runtime errors, set the following environment variable:

#### For Windows (CMD):
```bash
set KMP_DUPLICATE_LIB_OK=TRUE
```

#### For Windows (PowerShell):
```bash
$env:KMP_DUPLICATE_LIB_OK="TRUE"
```

#### For macOS/Linux:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

### Verify Installation

Check if Tesseract is correctly installed and accessible:

```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

If this shows the Tesseract version, the installation was successful.

## Application Configuration

### Step 1: Environment Setup

Create a directory structure for the application data:

```bash
# For Windows
mkdir uploads processed chroma_db

# For macOS/Linux
mkdir -p uploads processed chroma_db
```

### Step 2: Configure Settings (Optional)

Default settings are defined in `app/config/settings.py`. You can override these settings using environment variables:

#### For Windows (CMD):
```bash
set UPLOAD_DIR=C:\path\to\uploads
set PROCESSED_DIR=C:\path\to\processed
set CHROMA_DB_DIR=C:\path\to\chroma_db
set TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

#### For Windows (PowerShell):
```bash
$env:UPLOAD_DIR="C:\path\to\uploads"
$env:PROCESSED_DIR="C:\path\to\processed"
$env:CHROMA_DB_DIR="C:\path\to\chroma_db"
$env:TESSERACT_PATH="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

#### For macOS/Linux:
```bash
export UPLOAD_DIR=/path/to/uploads
export PROCESSED_DIR=/path/to/processed
export CHROMA_DB_DIR=/path/to/chroma_db
```

## Running the Application

### Option 1: Using the Batch Script (Windows)

For Windows users, simply run the provided batch script:

```bash
run.bat
```

This will:
1. Create necessary directories if they don't exist
2. Start the FastAPI backend on port 8000
3. Start the Streamlit frontend on port 8501

### Option 2: Using the Shell Script (macOS/Linux)

For macOS/Linux users, use the shell script:

```bash
chmod +x run.sh  # Make the script executable (first time only)
./run.sh
```

### Option 3: Running Components Manually

If you prefer to run the components separately:

#### Start the Backend (FastAPI):

```bash
# Activate your virtual environment if not already active
# For Windows:
# venv\Scripts\activate
# For macOS/Linux:
# source venv/bin/activate

# Run the FastAPI application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Start the Frontend (Streamlit):

In a separate terminal:

```bash
# Activate your virtual environment if not already active
# For Windows:
# venv\Scripts\activate
# For macOS/Linux:
# source venv/bin/activate

# Run the Streamlit application
python -m streamlit run app/frontend/main.py --server.port 8501 --server.address 0.0.0.0
```

### Accessing the Application

Once both services are running:

- **Backend API**: http://localhost:8000
  - API Documentation: http://localhost:8000/docs
  - OpenAPI Schema: http://localhost:8000/openapi.json

- **Frontend UI**: http://localhost:8501

## Development Workflow

### Code Structure

- `app/` - Main application code
  - `api/`