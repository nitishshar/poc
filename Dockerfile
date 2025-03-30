FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libpoppler-cpp-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads processed chroma_db

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    TESSERACT_PATH=/usr/bin/tesseract \
    UPLOAD_DIR=/app/uploads \
    PROCESSED_DIR=/app/processed \
    CHROMA_DB_DIR=/app/chroma_db

# Expose ports
EXPOSE 8000 8501

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 