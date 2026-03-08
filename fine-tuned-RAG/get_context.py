import sys
from rag_chain import get_retriever

def get_context(question):
    print(f"Querying for: {question}")
    retriever = get_retriever(k=5)
    docs = retriever.invoke(question)
    
    print("\n--- RETRIEVED CONTEXT ---")
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "Unknown")
        print(f"\n[Source {i+1}: {source}]")
        print(doc.page_content)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_context(sys.argv[1])
    else:
        print("Please provide a question.")
