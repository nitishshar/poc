import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Tuple

import PyPDF2
import pdfplumber

from app.models.document import TextChunk
from app.config.settings import settings

# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)


async def chunk_text(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200,
    file_path: Optional[str] = None
) -> List[TextChunk]:
    """
    Split text into semantically meaningful chunks.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        file_path: Optional path to the original file (for PDF coordinates)
        
    Returns:
        List of TextChunk objects
    """
    def _chunk():
        chunks = []
        
        # Extract any header/section information for better chunking
        sections = _extract_sections(text)
        
        if sections:
            # If we could extract sections, use them for chunking
            for section_title, section_text in sections:
                section_chunks = _chunk_by_size(
                    section_text, 
                    chunk_size, 
                    chunk_overlap
                )
                
                for i, chunk_text in enumerate(section_chunks):
                    chunks.append(TextChunk(
                        text=chunk_text,
                        section_title=section_title
                    ))
        else:
            # Otherwise, chunk by size
            chunked_texts = _chunk_by_size(text, chunk_size, chunk_overlap)
            chunks = [TextChunk(text=t) for t in chunked_texts]
        
        # If it's a PDF, try to add page numbers and coordinates
        if file_path and file_path.lower().endswith('.pdf'):
            chunks = _add_pdf_coordinates(file_path, chunks)
            
        return chunks
    
    return await asyncio.get_event_loop().run_in_executor(executor, _chunk)


def _extract_sections(text: str) -> List[Tuple[str, str]]:
    """Extract sections from text based on headers."""
    # Pattern for headers (e.g., "1. Introduction", "Chapter 5", etc.)
    header_patterns = [
        r'^#+\s+(.+)$',  # Markdown headers (# Header)
        r'^(\d+\.\s+.+)$',  # Numbered headers (1. Header)
        r'^(Chapter\s+\d+.*?)$',  # Chapter headers
        r'^(Section\s+\d+.*?)$',  # Section headers
        r'^([A-Z][A-Z\s]+)$'  # ALL CAPS headers
    ]
    
    # Combine patterns
    combined_pattern = '|'.join(f'({p})' for p in header_patterns)
    
    # Find potential headers
    lines = text.split('\n')
    sections = []
    current_header = "Introduction"
    current_content = []
    
    for line in lines:
        # Check if line matches header pattern
        if re.match(combined_pattern, line, re.MULTILINE):
            # If we have content, save the current section
            if current_content:
                sections.append((current_header, '\n'.join(current_content)))
            
            # Start a new section
            current_header = line.strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Add the last section
    if current_content:
        sections.append((current_header, '\n'.join(current_content)))
    
    # If we couldn't extract meaningful sections, return an empty list
    if len(sections) <= 1:
        return []
    
    return sections


def _chunk_by_size(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into chunks of specified size with overlap."""
    # First try to split by paragraphs
    paragraphs = _split_into_paragraphs(text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para.split())
        
        # If a single paragraph exceeds chunk size, split it further
        if para_size > chunk_size:
            # Process the current chunk if it's not empty
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split the large paragraph into sentences
            sentences = _split_into_sentences(para)
            sentence_chunks = _chunk_sentences(sentences, chunk_size, chunk_overlap)
            chunks.extend(sentence_chunks)
        
        # If adding this paragraph would exceed the chunk size, start a new chunk
        elif current_size + para_size > chunk_size:
            chunks.append(' '.join(current_chunk))
            
            # Keep some sentences from end of previous chunk for context
            overlap_words = _get_overlap_from_end(current_chunk, chunk_overlap)
            current_chunk = overlap_words + [para]
            current_size = len(' '.join(current_chunk).split())
            
        else:
            current_chunk.append(para)
            current_size += para_size
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


def _split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs based on blank lines."""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitting pattern
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
    sentences = re.split(sentence_pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def _chunk_sentences(sentences: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
    """Chunk sentences into maximum chunk_size word chunks with overlap."""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence.split())
        
        # If a single sentence exceeds chunk size, include it as its own chunk
        if sentence_size > chunk_size:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            chunks.append(sentence)
            continue
        
        # If adding this sentence would exceed the chunk size, start a new chunk
        if current_size + sentence_size > chunk_size:
            chunks.append(' '.join(current_chunk))
            
            # Keep some sentences from end of previous chunk for context
            overlap_words = _get_overlap_from_end(current_chunk, chunk_overlap)
            current_chunk = overlap_words + [sentence]
            current_size = len(' '.join(current_chunk).split())
        else:
            current_chunk.append(sentence)
            current_size += sentence_size
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


def _get_overlap_from_end(text_list: List[str], overlap_size: int) -> List[str]:
    """Get overlapping words from the end of the text list."""
    combined_text = ' '.join(text_list)
    words = combined_text.split()
    
    # Get the last 'overlap_size' words
    overlap_words = words[-overlap_size:] if len(words) > overlap_size else words
    overlap_text = ' '.join(overlap_words)
    
    # Find which chunks in the original list contain these words
    result = []
    remaining_words = overlap_size
    
    for item in reversed(text_list):
        if remaining_words <= 0:
            break
            
        word_count = len(item.split())
        if word_count <= remaining_words:
            result.insert(0, item)
            remaining_words -= word_count
        else:
            # Split the text to get only the needed words
            item_words = item.split()
            partial = ' '.join(item_words[-remaining_words:])
            result.insert(0, partial)
            break
    
    return result


def _add_pdf_coordinates(file_path: str, chunks: List[TextChunk]) -> List[TextChunk]:
    """Add page numbers and coordinates to chunks for PDFs."""
    try:
        # Extract page content with coordinates
        page_texts = _extract_pdf_text_with_coordinates(file_path)
        
        # Map chunks to pages and coordinates
        for chunk in chunks:
            chunk_text = chunk.text
            best_match = _find_best_match_page(chunk_text, page_texts)
            
            if best_match:
                page_num, coords = best_match
                chunk.page_number = page_num
                chunk.coordinates = coords
        
        return chunks
    except Exception as e:
        print(f"Error adding PDF coordinates: {str(e)}")
        return chunks


def _extract_pdf_text_with_coordinates(file_path: str) -> List[Dict]:
    """Extract text with coordinates from each page of a PDF."""
    page_texts = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                words = page.extract_words()
                text = ' '.join([w['text'] for w in words])
                
                # Calculate page boundaries
                x0, y0, x1, y1 = page.bbox
                
                page_texts.append({
                    'page_num': i,
                    'text': text,
                    'coordinates': {
                        'x1': x0,
                        'y1': y0,
                        'x2': x1,
                        'y2': y1
                    }
                })
        
        return page_texts
    except Exception as e:
        print(f"Error extracting PDF text with coordinates: {str(e)}")
        return []


def _find_best_match_page(chunk_text: str, page_texts: List[Dict]) -> Optional[Tuple[int, Dict]]:
    """Find the page that best matches the chunk text."""
    best_match = None
    highest_score = 0
    
    # Simple matching algorithm - could be improved with more sophisticated text matching
    for page in page_texts:
        page_text = page['text']
        
        # Calculate a simple overlap score
        words = set(chunk_text.split())
        page_words = set(page_text.split())
        common_words = words.intersection(page_words)
        
        if not common_words:
            continue
            
        score = len(common_words) / len(words)
        
        if score > highest_score:
            highest_score = score
            best_match = (page['page_num'], page['coordinates'])
    
    # Only return if we have a reasonably good match
    if highest_score > 0.3:
        return best_match
    
    return None 