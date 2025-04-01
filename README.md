# Document Chat

A modern web application that allows users to chat with their documents using various LLM providers.

## Features

- 📚 Multiple document support
- 🤖 Multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude)
- 💬 Context-aware responses
- 📊 Smart response visualization
- 🔄 Session management
- ⚡ Real-time updates
- 🎨 Modern UI with Streamlit

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/document-chat.git
cd document-chat
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

1. Start the backend API server:

```bash
python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Start the Streamlit frontend:

```bash
python -m streamlit run app/frontend/main.py
```

3. Open your browser and navigate to `http://localhost:8501`

## Configuration

The application can be configured using environment variables or by editing the `.env` file:

```env
# API Configuration
API_BASE_URL=http://localhost:8000/api
API_TIMEOUT=30
API_MAX_RETRIES=3
API_RETRY_DELAY=1.0

# Cache Configuration
CACHE_TTL=300
CACHE_MAX_ENTRIES=1000

# Session Configuration
SESSION_TIMEOUT=3600
MAX_SESSIONS_PER_USER=10
MAX_MESSAGES_PER_SESSION=100

# Document Configuration
MAX_DOCUMENT_SIZE=10485760  # 10MB
MAX_DOCUMENTS_PER_SESSION=5

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4

# Provider API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Project Structure

```
document-chat/
├── app/
│   ├── backend/         # FastAPI backend
│   │   ├── api/        # API endpoints
│   │   ├── core/       # Core functionality
│   │   ├── models/     # Data models
│   │   └── services/   # Business logic
│   └── frontend/       # Streamlit frontend
│       ├── components/ # UI components
│       ├── api.py      # API client
│       ├── config.py   # Configuration
│       ├── forms.py    # Form components
│       ├── main.py     # Main application
│       └── utils.py    # Utilities
├── tests/              # Test suite
├── docs/               # Documentation
├── .env.example        # Example environment variables
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Development

### Code Style

We use the following tools to maintain code quality:

- `black` for code formatting
- `isort` for import sorting
- `flake8` for linting
- `mypy` for type checking

Run the following commands before committing:

```bash
black .
isort .
flake8
mypy .
```

### Testing

Run tests with pytest:

```bash
pytest
```

Generate coverage report:

```bash
pytest --cov=app tests/
```

## Documentation

Generate documentation using MkDocs:

```bash
mkdocs serve  # Development server
mkdocs build  # Build static site
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Streamlit](https://streamlit.io/) for the amazing web framework
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- All the LLM providers for their powerful APIs
