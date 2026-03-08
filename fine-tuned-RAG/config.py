"""
config.py - Shared configuration loaded from .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Resolve DOCS_DIR relative to this file's directory
_rag_dir = Path(__file__).resolve().parent
_docs_raw = os.getenv("DOCS_DIR", "../../SDG/Hack Canada")
DOCS_DIR = str((_rag_dir / _docs_raw).resolve())

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "hack_canada")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
