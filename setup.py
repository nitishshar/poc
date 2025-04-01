from setuptools import find_packages, setup

# Read requirements.txt
with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read README.md
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="document-chat",
    version="1.0.0",
    description="A modern web application that allows users to chat with their documents using various LLM providers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/document-chat",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: FastAPI",
        "Framework :: Streamlit",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
    ],
    entry_points={
        "console_scripts": [
            "document-chat-api=app.backend.main:main",
            "document-chat-ui=app.frontend.main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/document-chat/issues",
        "Source": "https://github.com/yourusername/document-chat",
        "Documentation": "https://github.com/yourusername/document-chat/docs",
    },
) 