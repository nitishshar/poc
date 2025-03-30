import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings
from app.models.document import DocumentModel, TextChunk


# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_DB_DIR,
    settings=ChromaSettings(
        anonymized_telemetry=False
    )
)

# Initialize the embedding function
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=settings.EMBEDDING_MODEL
)


async def generate_embeddings(document: DocumentModel) -> str:
    """
    Generate and store embeddings for document chunks.
    
    Args:
        document: The document model containing text chunks
        
    Returns:
        The name of the collection where embeddings are stored
    """
    def _generate():
        # Create a unique collection name for this document
        collection_name = f"doc_{document.id}"
        
        # Get or create collection
        try:
            collection = chroma_client.get_collection(
                name=collection_name, 
                embedding_function=sentence_transformer_ef
            )
        except:
            collection = chroma_client.create_collection(
                name=collection_name,
                embedding_function=sentence_transformer_ef,
                metadata={"document_id": str(document.id)}
            )
        
        # Prepare data for embedding
        ids = []
        texts = []
        metadatas = []
        
        # Process text chunks
        for chunk in document.text_chunks:
            # Skip empty chunks
            if not chunk.text.strip():
                continue
                
            chunk_id = chunk.id
            chunk_text = chunk.text
            
            # Prepare metadata
            chunk_metadata = {
                "chunk_id": chunk_id,
                "document_id": str(document.id),
                "document_title": document.metadata.title if document.metadata else document.original_filename,
            }
            
            # Add optional metadata if available
            if chunk.page_number is not None:
                chunk_metadata["page_number"] = chunk.page_number
            
            if chunk.section_title:
                chunk_metadata["section_title"] = chunk.section_title
                
            if chunk.coordinates:
                chunk_metadata["coordinates"] = str(chunk.coordinates)
            
            ids.append(chunk_id)
            texts.append(chunk_text)
            metadatas.append(chunk_metadata)
        
        # Add special handling for tables if needed
        if settings.STORE_TABLES_SEPARATELY and document.tables:
            for table in document.tables:
                table_id = table.id
                
                # Convert table data to text
                header_text = ', '.join(table.header) if table.header else ""
                
                table_rows = []
                for row in table.data:
                    table_rows.append(', '.join(str(cell) for cell in row))
                
                table_text = header_text + "\n" + "\n".join(table_rows)
                
                # Skip empty tables
                if not table_text.strip():
                    continue
                
                # Prepare metadata
                table_metadata = {
                    "chunk_id": table_id,
                    "document_id": str(document.id),
                    "document_title": document.metadata.title if document.metadata else document.original_filename,
                    "is_table": True,
                    "page_number": table.page_number,
                    "rows": table.rows,
                    "columns": table.columns
                }
                
                if table.coordinates:
                    table_metadata["coordinates"] = str(table.coordinates)
                
                if table.caption:
                    table_metadata["caption"] = table.caption
                
                ids.append(table_id)
                texts.append(table_text)
                metadatas.append(table_metadata)
        
        # Store embeddings in chunks to avoid memory issues
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            # Add documents to the collection
            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas
            )
        
        return collection_name
    
    return await asyncio.get_event_loop().run_in_executor(executor, _generate)


async def query_embeddings(
    collection_name: str,
    query_text: str,
    n_results: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query embeddings from a collection.
    
    Args:
        collection_name: Name of the collection to query
        query_text: The query text
        n_results: Number of results to return
        filters: Optional filters to apply
        
    Returns:
        List of results with their metadata
    """
    def _query():
        try:
            collection = chroma_client.get_collection(
                name=collection_name,
                embedding_function=sentence_transformer_ef
            )
            
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filters
            )
            
            # Process results
            processed_results = []
            
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None,
                        "id": results['ids'][0][i]
                    }
                    processed_results.append(result)
            
            return processed_results
        except Exception as e:
            print(f"Error querying embeddings: {str(e)}")
            return []
    
    return await asyncio.get_event_loop().run_in_executor(executor, _query)


async def delete_collection(collection_name: str) -> bool:
    """Delete a collection from ChromaDB.
    
    Args:
        collection_name: The name of the collection to delete
        
    Returns:
        True if the collection was deleted, False otherwise
    """
    if not collection_name:
        return False
        
    try:
        # Check if collection exists
        try:
            chroma_client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, nothing to delete
            return True
            
        # Delete the collection
        chroma_client.delete_collection(name=collection_name)
        print(f"Deleted collection: {collection_name}")
        return True
    except Exception as e:
        print(f"Error deleting collection: {str(e)}")
        return False


async def get_collection_info(collection_name: str) -> Dict[str, Any]:
    """Get information about a collection."""
    try:
        collection = chroma_client.get_collection(name=collection_name)
        count = collection.count()
        return {
            "name": collection_name,
            "count": count
        }
    except Exception as e:
        print(f"Error getting collection info: {str(e)}")
        return {"name": collection_name, "count": 0, "error": str(e)} 