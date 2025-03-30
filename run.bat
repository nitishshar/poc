@echo off
ECHO Starting Document Processing Service...

REM Create necessary directories
if not exist uploads mkdir uploads
if not exist processed mkdir processed
if not exist chroma_db mkdir chroma_db

REM Start FastAPI backend
START "FastAPI Backend" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a moment for backend to start
TIMEOUT /T 3 /NOBREAK

REM Start Streamlit frontend
START "Streamlit Frontend" cmd /c "python -m streamlit run app/frontend/main.py --server.port 8501 --server.address 0.0.0.0"

ECHO Services started:
ECHO FastAPI backend:    http://localhost:8000
ECHO Streamlit frontend: http://localhost:8501
ECHO Close the terminal windows to stop the services.

PAUSE 