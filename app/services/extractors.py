import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict, Optional, Any
import pandas as pd
import PyPDF2
import pdfplumber
import pytesseract
import docx
from PIL import Image
import io
import csv
import re

from app.config.settings import settings
from app.models.document import TableInfo

# Configure pytesseract
if settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)


async def extract_text_from_pdf(file_path: str) -> Tuple[str, bool]:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (extracted_text, needs_ocr)
    """
    def _extract_with_pypdf():
        try:
            text = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"PyPDF2 extraction error: {str(e)}")
            return ""
    
    def _extract_with_pdfplumber():
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"pdfplumber extraction error: {str(e)}")
            return ""
    
    # Run both extractors in parallel
    pypdf_text = await asyncio.get_event_loop().run_in_executor(executor, _extract_with_pypdf)
    pdfplumber_text = await asyncio.get_event_loop().run_in_executor(executor, _extract_with_pdfplumber)
    
    # Choose the best result
    extracted_text = pypdf_text
    if len(pdfplumber_text) > len(pypdf_text):
        extracted_text = pdfplumber_text
    
    # Determine if OCR is needed
    needs_ocr = len(extracted_text.strip()) < 100  # Arbitrary threshold
    
    return extracted_text, needs_ocr


async def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    def _extract():
        try:
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            print(f"DOCX extraction error: {str(e)}")
            return ""
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract)


async def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a TXT file."""
    def _extract():
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                return file.read()
        except Exception as e:
            print(f"TXT extraction error: {str(e)}")
            return ""
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract)


async def extract_text_from_csv(file_path: str) -> str:
    """Extract text from a CSV or Excel file."""
    def _extract():
        try:
            if file_path.endswith(('.csv')):
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    reader = csv.reader(file)
                    rows = list(reader)
                    return "\n".join([",".join(row) for row in rows])
            else:  # Excel files
                df = pd.read_excel(file_path)
                return df.to_string(index=False)
        except Exception as e:
            print(f"CSV/Excel extraction error: {str(e)}")
            return ""
    
    return await asyncio.get_event_loop().run_in_executor(executor, _extract)


async def perform_ocr(file_path: str) -> str:
    """
    Perform OCR on a document to extract text from images.
    
    Args:
        file_path: Path to the document
        
    Returns:
        Extracted text from OCR
    """
    def _perform_ocr_pdf():
        try:
            text = ""
            if file_path.lower().endswith('.pdf'):
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        # Extract image objects from the page
                        for img in page.images:
                            # Get the image
                            image = page.to_image()
                            # Perform OCR
                            ocr_text = pytesseract.image_to_string(
                                image.original, 
                                lang=settings.OCR_LANGUAGE
                            )
                            text += ocr_text + " "
                        
                        # Also try OCR on the entire page
                        image = page.to_image()
                        page_text = pytesseract.image_to_string(
                            image.original,
                            lang=settings.OCR_LANGUAGE
                        )
                        text += page_text + " "
            else:
                # For non-PDF files, assume it's an image
                img = Image.open(file_path)
                text = pytesseract.image_to_string(
                    img, 
                    lang=settings.OCR_LANGUAGE
                )
            return text
        except Exception as e:
            print(f"OCR error: {str(e)}")
            return ""
    
    return await asyncio.get_event_loop().run_in_executor(executor, _perform_ocr_pdf)


async def extract_tables(file_path: str, file_type: str) -> List[TableInfo]:
    """
    Extract tables from a document.
    
    Args:
        file_path: Path to the document
        file_type: Type of the document
        
    Returns:
        List of TableInfo objects
    """
    def _extract_tables_from_pdf():
        tables = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for i, table_data in enumerate(page_tables):
                        if table_data:
                            # Process the table data
                            header = table_data[0] if len(table_data) > 0 else None
                            data = table_data[1:] if len(table_data) > 1 else []
                            
                            # Get table coordinates
                            table_bbox = page.find_tables()[i].bbox if i < len(page.find_tables()) else (0, 0, 0, 0)
                            
                            table = TableInfo(
                                page_number=page_num,
                                rows=len(table_data),
                                columns=len(table_data[0]) if table_data and table_data[0] else 0,
                                coordinates={
                                    "x1": table_bbox[0],
                                    "y1": table_bbox[1],
                                    "x2": table_bbox[2],
                                    "y2": table_bbox[3]
                                },
                                header=header,
                                data=data
                            )
                            tables.append(table)
            return tables
        except Exception as e:
            print(f"Table extraction error: {str(e)}")
            return []
    
    def _extract_tables_from_docx():
        # Placeholder: DOCX table extraction is complex
        # In a real implementation, would use python-docx's table API
        return []
    
    def _extract_tables_from_excel():
        tables = []
        try:
            # For Excel files, each sheet is treated as a table
            if file_path.endswith(('.xlsx', '.xls')):
                xl = pd.ExcelFile(file_path)
                for sheet_name in xl.sheet_names:
                    df = xl.parse(sheet_name)
                    data = df.values.tolist()
                    header = df.columns.tolist()
                    
                    table = TableInfo(
                        page_number=1,  # Excel doesn't have pages
                        rows=len(data) + 1,  # +1 for header
                        columns=len(header),
                        coordinates={"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # No coordinates for Excel
                        header=header,
                        data=data,
                        caption=sheet_name
                    )
                    tables.append(table)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
                data = df.values.tolist()
                header = df.columns.tolist()
                
                table = TableInfo(
                    page_number=1,  # CSV doesn't have pages
                    rows=len(data) + 1,  # +1 for header
                    columns=len(header),
                    coordinates={"x1": 0, "y1": 0, "x2": 0, "y2": 0},  # No coordinates for CSV
                    header=header,
                    data=data
                )
                tables.append(table)
            return tables
        except Exception as e:
            print(f"Excel/CSV table extraction error: {str(e)}")
            return []
    
    if file_type.endswith('pdf'):
        return await asyncio.get_event_loop().run_in_executor(executor, _extract_tables_from_pdf)
    elif file_type.endswith(('xlsx', 'xls', 'csv')):
        return await asyncio.get_event_loop().run_in_executor(executor, _extract_tables_from_excel)
    elif file_type.endswith(('docx', 'doc')):
        return await asyncio.get_event_loop().run_in_executor(executor, _extract_tables_from_docx)
    else:
        return [] 