"""
retriever.py - Vector store retrieval logic for the Hack Canada RAG system.
"""
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, OPENAI_API_KEY


def get_vectorstore() -> Chroma:
    """Load the persisted ChromaDB vectorstore."""
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=OPENAI_API_KEY
    )
    return Chroma(
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )


def search(query: str, k: int = 5, use_mmr: bool = False) -> list[dict]:
    """
    Search the vector store for relevant chunks.

    Args:
        query: The search query
        k: Number of results to return
        use_mmr: If True, use Maximal Marginal Relevance for diversity

    Returns:
        List of dicts with 'content', 'metadata', and 'score'
    """
    vs = get_vectorstore()

    if use_mmr:
        docs = vs.max_marginal_relevance_search(query, k=k, fetch_k=k * 3)
        # MMR doesn't return scores directly
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": None
            }
            for doc in docs
        ]
    else:
        results = vs.similarity_search_with_relevance_scores(query, k=k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": round(score, 4)
            }
            for doc, score in results
        ]


def get_retriever(k: int = 5):
    """Get a LangChain retriever object for use in chains."""
    vs = get_vectorstore()
    return vs.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )


def get_collection_stats() -> dict:
    """Get stats about the ChromaDB collection."""
    vs = get_vectorstore()
    collection = vs._collection
    count = collection.count()

    # Sample some metadata to show source distribution
    sample = collection.peek(min(count, 50))
    source_types = {}
    filenames = set()
    if sample and "metadatas" in sample:
        for meta in sample["metadatas"]:
            st = meta.get("source_type", "unknown")
            source_types[st] = source_types.get(st, 0) + 1
            filenames.add(meta.get("filename", "unknown"))

    return {
        "total_chunks": count,
        "sample_source_types": source_types,
        "sample_unique_files": len(filenames)
    }
