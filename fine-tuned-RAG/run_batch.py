import json
import sys
from rag_chain import get_retriever

def main():
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    with open("../synthetic_data.json", "r") as f:
        data = json.load(f)
        
    retriever = get_retriever(k=4)
    count = 0
    
    for category in data:
        for subtopic in category.get("subtopics", []):
            for entry in subtopic.get("entries", []):
                # Only process if we haven't manually answered it yet
                if not entry.get("manual_rag"):
                    print(f"\n=======================================================")
                    print(f"QUESTION: {entry['input']}")
                    docs = retriever.invoke(entry['input'])
                    for doc_idx, doc in enumerate(docs):
                        print(f"\n--- SOURCE {doc_idx+1}: {doc.metadata.get('source')} ---")
                        print(doc.page_content[:800] + "...")
                    
                    count += 1
                    if count >= batch_size:
                        return
                        
    if count == 0:
        print("ALL DONE!")

if __name__ == "__main__":
    main()
