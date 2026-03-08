"""
api.py - FastAPI server for the Hack Canada RAG system.

Endpoints:
    POST /query   - Raw similarity search (returns chunks + sources)
    POST /ask     - Full RAG answer with citations
    GET  /health  - Health check
    GET  /stats   - Collection statistics
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from retriever import search, get_collection_stats
from rag_chain import ask as rag_ask

app = FastAPI(
    title="Hack Canada RAG API",
    description="Retrieval-Augmented Generation API for Ontario planning & zoning intelligence",
    version="1.0.0"
)

# Allow CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    k: int = Field(5, ge=1, le=20, description="Number of results")
    use_mmr: bool = Field(False, description="Use MMR for diverse results")


class AskRequest(BaseModel):
    question: str = Field(..., description="Question to answer")
    k: int = Field(5, ge=1, le=20, description="Number of source chunks to retrieve")


class ChunkResult(BaseModel):
    content: str
    metadata: dict
    score: float | None


class QueryResponse(BaseModel):
    query: str
    results: list[ChunkResult]
    count: int


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]
    num_sources: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "hack-canada-rag"}


@app.get("/stats")
async def stats():
    """Get collection statistics."""
    try:
        return get_collection_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """
    Raw similarity search — returns the most relevant chunks with sources.
    Good for inspection and debugging.
    """
    try:
        results = search(req.query, k=req.k, use_mmr=req.use_mmr)
        return QueryResponse(
            query=req.query,
            results=[ChunkResult(**r) for r in results],
            count=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """
    Full RAG pipeline — retrieves relevant context and generates an answer
    with citations from Ontario planning documents.
    """
    try:
        result = rag_ask(req.question, k=req.k)
        return AskResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8100, reload=True)
