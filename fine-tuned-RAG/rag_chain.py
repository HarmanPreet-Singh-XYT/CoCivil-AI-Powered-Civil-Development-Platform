"""
rag_chain.py - RAG chain that retrieves context and generates answers with citations.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from config import LLM_MODEL, OPENAI_API_KEY
from retriever import get_retriever


SYSTEM_PROMPT = """You are an expert Ontario planning and zoning assistant for the Buildability Intelligence Pipeline. 
You help developers, planners, and land acquisition teams assess site feasibility under Ontario's regulatory framework.

Your knowledge comes from official Toronto/Ontario planning and municipal documents including:
- Toronto Official Plan chapters
- Zoning By-laws (569-2013 and site-specific amendments)
- Secondary Plans (Downtown, North York Centre, Yonge-Eglinton, etc.)
- Ontario Building Code Act and Building Code regulations
- Ontario Planning Act
- Conservation authority regulations
- Heritage planning controls
- City planning maps (land use, zoning, environmental, transit)
- Ontario water policy: Safe Drinking Water Act, Ontario Water Resources Act, O. Reg. 170/03, O. Reg. 169/03
- Water infrastructure: meter reading, billing, permits, source protection, MTU replacement zones
- Municipal water system design guidelines and drinking water quality standards

When answering:
1. ALWAYS cite the specific document/source for each claim (e.g., "According to the Toronto Official Plan Chapter 3...")
2. Distinguish between HARD RULES (legally binding) and SOFT GUIDANCE (policy direction)
3. Flag any UNCERTAINTIES or areas where the user should verify with the municipality
4. Provide specific section/page references when available
5. Wherever possible, quote the exact verbatim text of the law, by-law, or policy to support your claims. Put the quote in quotation marks.
6. If the retrieved context doesn't contain enough information to fully answer, say so explicitly

RETRIEVED CONTEXT:
{context}
"""

USER_TEMPLATE = """{question}"""


def format_docs(docs) -> str:
    """Format retrieved documents into a context string."""
    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Unknown")
        source_type = doc.metadata.get("source_type", "unknown")
        page = doc.metadata.get("page", "")
        page_str = f" (page {page})" if page else ""

        parts.append(
            f"--- Source {i}: [{source_type}] {source}{page_str} ---\n"
            f"{doc.page_content}\n"
        )
    return "\n".join(parts)


def get_rag_chain(k: int = 5):
    """Build and return the RAG chain."""
    retriever = get_retriever(k=k)
    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        temperature=0.1
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_TEMPLATE)
    ])

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def ask(question: str, k: int = 5) -> dict:
    """
    Ask a question using the RAG chain.

    Returns dict with 'answer', 'sources', and 'question'.
    """
    retriever = get_retriever(k=k)
    chain = get_rag_chain(k=k)

    # Get source docs for citation
    source_docs = retriever.invoke(question)
    answer = chain.invoke(question)

    sources = []
    for doc in source_docs:
        sources.append({
            "source": doc.metadata.get("source", "Unknown"),
            "source_type": doc.metadata.get("source_type", "unknown"),
            "page": doc.metadata.get("page"),
            "excerpt": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        })

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "num_sources": len(sources)
    }
