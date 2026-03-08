"""
ingest.py - Document ingestion pipeline for the Hack Canada RAG system.

Walks the DOCS_DIR, extracts text from PDFs/MD/JSON, captions PNGs via GPT-4o Vision,
chunks everything, and stores embeddings in ChromaDB.

Usage:
    python ingest.py              # Full ingestion
    python ingest.py --png-only   # Only process PNG files (for re-captioning)
"""
import os
import sys
import json
import base64
import time
from pathlib import Path
from typing import Generator

import fitz  # PyMuPDF
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import (
    DOCS_DIR, CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP,
    COLLECTION_NAME, EMBEDDING_MODEL, OPENAI_API_KEY
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pdf_to_text(path: str) -> list[dict]:
    """Extract text from PDF, returning list of {page, text}."""
    results = []
    try:
        doc = fitz.open(path)
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                results.append({"page": i + 1, "text": text.strip()})
        doc.close()
    except Exception as e:
        print(f"  ⚠ PyMuPDF failed on {path}: {e}")
    return results


def md_to_text(path: str) -> str:
    """Read markdown file as plain text."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def json_to_text(path: str, max_records: int = 500) -> str:
    """Extract text from JSON. For large files, take a sample."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        if isinstance(data, list):
            # Sample records to avoid enormous chunks
            sample = data[:max_records]
            lines = []
            for record in sample:
                if isinstance(record, dict):
                    lines.append(" | ".join(
                        f"{k}: {v}" for k, v in record.items()
                        if v is not None and str(v).strip()
                    ))
                else:
                    lines.append(str(record))
            return "\n".join(lines)
        elif isinstance(data, dict):
            return json.dumps(data, indent=2, ensure_ascii=False)[:50000]
        else:
            return str(data)[:50000]
    except Exception as e:
        print(f"  ⚠ JSON parse failed on {path}: {e}")
        return ""


def caption_png(path: str, client: OpenAI) -> str:
    """Use GPT-4o Vision to generate a detailed textual description of a map/image."""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    filename = os.path.basename(path)
    prompt = (
        f"This is a Toronto/Ontario city planning map or diagram named '{filename}'. "
        "Describe it in thorough detail for use in a planning knowledge base. Include:\n"
        "1. What type of map/diagram this is (zoning, land use, transit, environmental, etc.)\n"
        "2. All text labels, zone codes, legend entries, and area names visible\n"
        "3. Key spatial relationships, boundaries, and notable features\n"
        "4. Any numbers, measurements, or data shown\n"
        "5. The geographic area covered\n"
        "Be thorough — this description will be the only searchable representation of this map."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                        "detail": "high"
                    }}
                ]
            }],
            max_tokens=2000
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"  ⚠ Vision captioning failed for {path}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Document loader
# ---------------------------------------------------------------------------

def load_all_documents(png_only: bool = False) -> Generator[Document, None, None]:
    """Walk DOCS_DIR and yield LangChain Documents."""
    docs_path = Path(DOCS_DIR)
    if not docs_path.exists():
        print(f"❌ DOCS_DIR not found: {DOCS_DIR}")
        sys.exit(1)

    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    file_count = 0

    for root, dirs, files in os.walk(docs_path):
        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, DOCS_DIR)
            ext = os.path.splitext(filename)[1].lower()

            # Skip hidden files
            if filename.startswith("."):
                continue

            # PNG only mode
            if png_only and ext != ".png":
                continue

            # Skip non-PNG in normal mode if flagged
            if not png_only and ext in (".ds_store",):
                continue

            file_count += 1
            print(f"  [{file_count}] Processing: {rel_path} ({ext})")

            if ext == ".pdf":
                pages = pdf_to_text(filepath)
                if not pages:
                    print(f"       → No text extracted")
                    continue
                for page_data in pages:
                    yield Document(
                        page_content=page_data["text"],
                        metadata={
                            "source": rel_path,
                            "source_type": "pdf",
                            "page": page_data["page"],
                            "filename": filename
                        }
                    )
                print(f"       → {len(pages)} pages extracted")

            elif ext in (".md", ".txt"):
                text = md_to_text(filepath)
                if text.strip():
                    yield Document(
                        page_content=text,
                        metadata={
                            "source": rel_path,
                            "source_type": "markdown",
                            "filename": filename
                        }
                    )
                    print(f"       → {len(text)} chars")

            elif ext == ".json":
                # Skip very large JSON files (>50MB) to avoid memory issues
                fsize = os.path.getsize(filepath)
                if fsize > 50_000_000:
                    print(f"       → Skipping (too large: {fsize / 1e6:.0f}MB)")
                    continue
                text = json_to_text(filepath)
                if text.strip():
                    yield Document(
                        page_content=text,
                        metadata={
                            "source": rel_path,
                            "source_type": "json",
                            "filename": filename
                        }
                    )
                    print(f"       → {len(text)} chars")

            elif ext == ".png":
                if not openai_client:
                    print(f"       → Skipping PNG (no OPENAI_API_KEY)")
                    continue
                # Check file size - skip very large images
                fsize = os.path.getsize(filepath)
                if fsize > 20_000_000:
                    print(f"       → Skipping PNG (too large: {fsize / 1e6:.0f}MB)")
                    continue

                caption = caption_png(filepath, openai_client)
                if caption.strip():
                    yield Document(
                        page_content=f"[MAP DESCRIPTION: {filename}]\n\n{caption}",
                        metadata={
                            "source": rel_path,
                            "source_type": "map_image",
                            "filename": filename
                        }
                    )
                    print(f"       → Captioned ({len(caption)} chars)")
                    # Rate limit to avoid hitting API limits
                    time.sleep(1)

            else:
                print(f"       → Skipping unsupported format")


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------

def run_ingestion(png_only: bool = False):
    """Main ingestion pipeline."""
    print("=" * 60)
    print("🚀 Hack Canada RAG Ingestion Pipeline")
    print("=" * 60)
    print(f"  Docs dir:    {DOCS_DIR}")
    print(f"  Chroma dir:  {CHROMA_DIR}")
    print(f"  Chunk size:  {CHUNK_SIZE} / overlap: {CHUNK_OVERLAP}")
    print(f"  Collection:  {COLLECTION_NAME}")
    print(f"  Embeddings:  {EMBEDDING_MODEL}")
    print(f"  PNG only:    {png_only}")
    print()

    # 1. Load documents
    print("📄 Loading documents...")
    all_docs = list(load_all_documents(png_only=png_only))
    print(f"\n✅ Loaded {len(all_docs)} raw documents")

    if not all_docs:
        print("❌ No documents loaded. Check DOCS_DIR path.")
        return

    # 2. Chunk documents
    print("\n✂️  Chunking documents...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in all_docs:
        # Don't chunk map descriptions (they're already concise)
        if doc.metadata.get("source_type") == "map_image":
            chunks.append(doc)
        else:
            split_docs = splitter.split_documents([doc])
            chunks.extend(split_docs)

    print(f"✅ Created {len(chunks)} chunks")

    # 3. Create embeddings and store in ChromaDB
    print("\n🧠 Embedding and storing in ChromaDB...")
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=OPENAI_API_KEY
    )

    # Process in batches to avoid rate limits
    batch_size = 100
    vectorstore = None

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=CHROMA_DIR,
                collection_name=COLLECTION_NAME
            )
        else:
            vectorstore.add_documents(batch)

    if vectorstore:
        # Print stats
        collection = vectorstore._collection
        count = collection.count()
        print(f"\n{'=' * 60}")
        print(f"✅ Ingestion complete!")
        print(f"   Total chunks in store: {count}")
        print(f"   ChromaDB location: {os.path.abspath(CHROMA_DIR)}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    png_only = "--png-only" in sys.argv
    run_ingestion(png_only=png_only)
