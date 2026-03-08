import json
import time
import os
import concurrent.futures

from rag_chain import get_rag_chain, get_retriever

JSON_PATH = "../synthetic_data.json"

TARGET_SUBTOPICS = [
    "Urban Design Guidelines",
    "Ontario Building Code Compliance",
    "Heritage Preservation Requirements",
    "Wetland Protection Regulations",
    "Environmental Site Assessment (ESA) Protocols in Ontario",
    "Archaeological Assessments in Construction Planning",
    "Stormwater Management and Flood Risk",
    "Transportation & Access Constraints (Entrances, Sightlines, Parking)"
]

# Initialize globally
print("Initializing RAG chain...")
GLOBAL_RETRIEVER = get_retriever(k=5)
GLOBAL_CHAIN = get_rag_chain(k=5)

def process_entry(entry):
    question = entry.get("input")
    try:
        source_docs = GLOBAL_RETRIEVER.invoke(question)
        answer = GLOBAL_CHAIN.invoke(question)

        sources = []
        for doc in source_docs:
            sources.append({
                "source": doc.metadata.get("source", "Unknown"),
                "source_type": doc.metadata.get("source_type", "unknown")
            })

        formatted_output = f"{answer}\n\n"
        if len(sources) > 0:
            formatted_output += "Sources:\n"
            for s in sources:
                formatted_output += f"- {s.get('source')} (Type: {s.get('source_type')})\n"
        
        entry["output"] = formatted_output
        return True
    except Exception as e:
        print(f"❌ Error on '{question[:30]}': {e}")
        return False

def process_file():
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    
    entries_to_process = []
    
    for topic in data:
        for subtopic in topic.get("subtopics", []):
            subtopic_name = subtopic.get("subtopic", "")
            
            # Check if this subtopic is one of the targets (or starts with one, to handle truncation)
            is_target = any(target in subtopic_name for target in TARGET_SUBTOPICS)
            
            # Since the user might have missed some in the paste, let's also look for topic matches
            # from their paste.
            target_topics = [
                "Development Approvals Workflow",
                "Building Code Act & Ontario Building Code Compliance Triggers",
                "Conservation Authorities & Regulated Areas",
                "Environmental Constraints",
                "Heritage Planning",
                "Servicing & Infrastructure Capacity",
                "Transportation & Access Constraints"
            ]
            is_topic_target = any(target in topic.get("topic", "") for target in target_topics)
            
            if is_target or is_topic_target:
                for entry in subtopic.get("entries", []):
                    entries_to_process.append(entry)
                    
    total = len(entries_to_process)
    print(f"Reprocessing {total} selected entries directly using RAG...")
    
    processed = 0
    # Process sequentially
    for entry in entries_to_process:
        process_entry(entry)
        processed += 1
        if processed % 10 == 0:
            print(f"[{processed}/{total}] Completed requests...")
            
            # Save progress periodically
            with open(JSON_PATH, "w") as f:
                json.dump(data, f, indent=2)

    # Final save
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print("Success! Finished repopulating selected entries.")

if __name__ == "__main__":
    process_file()
