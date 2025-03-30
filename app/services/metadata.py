import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Any, Optional

import PyPDF2
import docx
import pandas as pd

from app.models.document import DocumentMetadata
from app.config.settings import settings

# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)


async def extract_metadata(file_path: str, file_type: str) -> DocumentMetadata:
    """
    Extract metadata from a document.
    
    Args:
        file_path: Path to the document
        file_type: Type of the document
        
    Returns:
        DocumentMetadata object
    """
    if file_type.endswith('pdf'):
        return await _extract_pdf_metadata(file_path)
    elif file_type.endswith(('docx', 'doc')):
        return await _extract_docx_metadata(file_path)
    elif file_type.endswith('txt'):
        return await _extract_txt_metadata(file_path)
    elif file_type.endswith(('csv', 'xlsx', 'xls')):
        return await _extract_excel_metadata(file_path)
    else:
        return DocumentMetadata(
            title=os.path.basename(file_path),
            content_type=file_type
        )


async def _extract_pdf_metadata(file_path: str) -> DocumentMetadata:
    """Extract metadata from a PDF file."""
    def _extract():
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                info = reader.metadata
                
                # Count words in the document
                word_count = 0
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        word_count += len(text.split())
                
                # Parse dates
                created_date = None
                modified_date = None
                
                if info and '/CreationDate' in info:
                    try:
                        created_str = info['/CreationDate']
                        if isinstance(created_str, str) and created_str.startswith('D:'):
                            # PDF date format: D:YYYYMMDDHHmmSS
                            created_str = created_str[2:]  # Remove 'D:'
                            created_date = datetime.strptime(created_str[:14], '%Y%m%d%H%M%S')
                    except Exception:
                        pass
                
                if info and '/ModDate' in info:
                    try:
                        modified_str = info['/ModDate']
                        if isinstance(modified_str, str) and modified_str.startswith('D:'):
                            # PDF date format: D:YYYYMMDDHHmmSS
                            modified_str = modified_str[2:]  # Remove 'D:'
                            modified_date = datetime.strptime(modified_str[:14], '%Y%m%d%H%M%S')
                    except Exception:
                        pass
                
                # Extract custom metadata
                custom_metadata = {}
                if info:
                    for key, value in info.items():
                        if key not in ['/Title', '/Author', '/CreationDate', '/ModDate']:
                            # Clean key name
                            clean_key = key.replace('/', '').lower()
                            custom_metadata[clean_key] = str(value)
                
                return DocumentMetadata(
                    title=info.get('/Title', os.path.basename(file_path)) if info else os.path.basename(file_path),
                    author=info.get('/Author', None) if info else None,
                    created_date=created_date,
                    modified_date=modified_date,
                    page_count=len(reader.pages),
                    word_count=word_count,
                    content_type="application/pdf",
                    custom_metadata=custom_metadata
                )
        except Exception as e:
            print(f"PDF metadata extraction error: {str(e)}")
            return DocumentMetadata(
                title=os.path.basename(file_path),
                content_type="application/pdf"
            )
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract)


async def _extract_docx_metadata(file_path: str) -> DocumentMetadata:
    """Extract metadata from a DOCX file."""
    def _extract():
        try:
            doc = docx.Document(file_path)
            
            # Get core properties
            core_props = doc.core_properties
            
            # Count words
            word_count = 0
            for para in doc.paragraphs:
                word_count += len(para.text.split())
            
            # Extract custom metadata
            custom_metadata = {}
            for prop_name in dir(core_props):
                if not prop_name.startswith('_') and prop_name not in [
                    'title', 'author', 'created', 'modified', 'content_type'
                ]:
                    value = getattr(core_props, prop_name)
                    if value is not None:
                        custom_metadata[prop_name] = str(value)
            
            return DocumentMetadata(
                title=core_props.title or os.path.basename(file_path),
                author=core_props.author,
                created_date=core_props.created,
                modified_date=core_props.modified,
                word_count=word_count,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                custom_metadata=custom_metadata
            )
        except Exception as e:
            print(f"DOCX metadata extraction error: {str(e)}")
            return DocumentMetadata(
                title=os.path.basename(file_path),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract)


async def _extract_txt_metadata(file_path: str) -> DocumentMetadata:
    """Extract metadata from a TXT file."""
    def _extract():
        try:
            # For text files, just get basic file info
            stat = os.stat(file_path)
            created_date = datetime.fromtimestamp(stat.st_ctime)
            modified_date = datetime.fromtimestamp(stat.st_mtime)
            
            # Count words
            word_count = 0
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                for line in file:
                    word_count += len(line.split())
            
            return DocumentMetadata(
                title=os.path.basename(file_path),
                created_date=created_date,
                modified_date=modified_date,
                word_count=word_count,
                content_type="text/plain"
            )
        except Exception as e:
            print(f"TXT metadata extraction error: {str(e)}")
            return DocumentMetadata(
                title=os.path.basename(file_path),
                content_type="text/plain"
            )
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract)


async def _extract_excel_metadata(file_path: str) -> DocumentMetadata:
    """Extract metadata from an Excel/CSV file."""
    def _extract():
        try:
            # Get basic file info
            stat = os.stat(file_path)
            created_date = datetime.fromtimestamp(stat.st_ctime)
            modified_date = datetime.fromtimestamp(stat.st_mtime)
            
            # For Excel files, get sheet info
            custom_metadata = {}
            
            if file_path.endswith(('.xlsx', '.xls')):
                xl = pd.ExcelFile(file_path)
                sheet_names = xl.sheet_names
                custom_metadata['sheet_names'] = ', '.join(sheet_names)
                custom_metadata['sheet_count'] = str(len(sheet_names))
                
                # Get cell count as a measure of "word count"
                word_count = 0
                for sheet in sheet_names:
                    df = xl.parse(sheet)
                    word_count += df.size
                
                content_type = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" 
                               if file_path.endswith('.xlsx') else "application/vnd.ms-excel")
            else:  # CSV
                df = pd.read_csv(file_path)
                word_count = df.size
                custom_metadata['column_count'] = str(len(df.columns))
                custom_metadata['row_count'] = str(len(df))
                content_type = "text/csv"
            
            return DocumentMetadata(
                title=os.path.basename(file_path),
                created_date=created_date,
                modified_date=modified_date,
                word_count=word_count,
                content_type=content_type,
                custom_metadata=custom_metadata
            )
        except Exception as e:
            print(f"Excel/CSV metadata extraction error: {str(e)}")
            return DocumentMetadata(
                title=os.path.basename(file_path),
                content_type="application/spreadsheet"
            )
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract) 