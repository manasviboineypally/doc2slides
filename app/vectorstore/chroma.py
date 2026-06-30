"""
ChromaDB vector store for Doc2Slides.

This module handles:
1. Chunking sections into smaller pieces
2. Embedding chunks (ChromaDB does this automatically by default)
3. Storing chunks in a persistent vector DB
4. Searching chunks by semantic similarity

Default embedding model: all-MiniLM-L6-v2 (ChromaDB ships with this).
It's small, fast, and runs locally — no API keys needed.
"""
from pathlib import Path
from typing import List
import chromadb
from chromadb.config import Settings
from app.schemas.document import ParsedDocument, Section


# Where the vector DB persists on disk
CHROMA_DIR = Path("chroma_db")
CHROMA_DIR.mkdir(exist_ok=True)


# Create a single client we reuse across the app
_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False),
)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping word-based chunks.
    
    Why overlap? If a key sentence sits right at a chunk boundary, it 
    gets split awkwardly. Overlap means each idea is fully present in 
    at least one chunk.
    
    Args:
        text: the raw text to chunk
        chunk_size: target words per chunk
        overlap: words shared between consecutive chunks
    
    Returns:
        list of chunk strings
    """
    words = text.split()
    if not words:
        return []
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap  # step back for overlap
    
    return chunks


def index_document(doc: ParsedDocument, collection_name: str = "default") -> dict:
    """
    Chunk every section of a parsed document and add it to ChromaDB.
    
    Each chunk becomes a row in the collection with metadata so we 
    can trace it back: which section it came from, which page, etc.
    
    Returns a dict with stats: total chunks added, chunks per section.
    """
    # Get or create the collection (named bucket of vectors)
    collection = _client.get_or_create_collection(name=collection_name)
    
    # If this doc was already indexed, clear it first to avoid duplicates
    existing = collection.get(where={"source_file": doc.source_file})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
    
    all_ids: List[str] = []
    all_chunks: List[str] = []
    all_metadata: List[dict] = []
    
    chunks_per_section = {}
    
    for section in doc.sections:
        chunks = chunk_text(section.content)
        chunks_per_section[section.id] = len(chunks)
        
        for chunk_idx, chunk_text_str in enumerate(chunks):
            chunk_id = f"{section.id}_chunk_{chunk_idx}"
            all_ids.append(chunk_id)
            all_chunks.append(chunk_text_str)
            all_metadata.append({
                "source_file": doc.source_file,
                "section_id": section.id,
                "section_heading": section.heading,
                "page": section.page,
                "chunk_index": chunk_idx,
            })
    
    # ChromaDB embeds + stores everything in one call
    if all_chunks:
        collection.add(
            ids=all_ids,
            documents=all_chunks,
            metadatas=all_metadata,
        )
    
    return {
        "total_chunks": len(all_chunks),
        "chunks_per_section": chunks_per_section,
        "collection_name": collection_name,
    }


def search(
    query: str,
    collection_name: str = "default",
    source_file: str = None,
    top_k: int = 5,
) -> List[dict]:
    """
    Search for chunks similar to the query.
    
    Args:
        query: natural language question
        collection_name: which collection to search
        source_file: if given, only search chunks from this document
        top_k: how many results to return
    
    Returns:
        list of {text, metadata, distance} dicts, sorted by similarity
    """
    collection = _client.get_or_create_collection(name=collection_name)
    
    # Filter by source file if requested
    where = {"source_file": source_file} if source_file else None
    
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
    )
    
    # ChromaDB returns parallel arrays — zip them into nice dicts
    output = []
    for i, doc_text in enumerate(results["documents"][0]):
        output.append({
            "text": doc_text,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],  # lower = more similar
        })
    
    return output