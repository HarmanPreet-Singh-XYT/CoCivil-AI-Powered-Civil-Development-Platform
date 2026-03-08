import json
import requests
import time
import os
import concurrent.futures

JSON_PATH = "/Applications/Development/HackCanada/SDG/synthetic_data.json"
API_URL = "http://localhost:8100/ask"

def process_entry(entry):
    question = entry.get("input")
    try:
        resp = requests.post(API_URL, json={"question": question, "k": 3})
        resp.raise_for_status()
        answer_data = resp.json()
        
        answer = answer_data.get("answer", "")
        sources = answer_data.get("sources", [])
        num_sources = answer_data.get("num_sources", 0)
        
        formatted_output = f"{answer}\\n\\n"
        if num_sources > 0:
            formatted_output += "Sources:\\n"
            for i, s in enumerate(sources):
                formatted_output += f"- {s.get('source')} (Type: {s.get('source_type')})\\n"
        
        entry["output"] = formatted_output
        return True
    except Exception as e:
        print(f"❌ Error on '{question[:30]}': {e}")
        return False

def process_file():
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    
    entries_to_process = []
    
    # We will re-process ALL entries to ensure quotes are included
    for topic in data:
        for subtopic in topic.get("subtopics", []):
            for entry in subtopic.get("entries", []):
                entries_to_process.append(entry)
                    
    total = len(entries_to_process)
    print(f"Reprocessing all {total} entries...")
    
    # Using 5 parallel workers
    processed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_to_entry = {executor.submit(process_entry, entry): entry for entry in entries_to_process}
        for future in concurrent.futures.as_completed(future_to_entry):
            processed += 1
            if processed % 10 == 0:
                print(f"[{processed}/{total}] Completed requests...")
                
                # Save progress
                with open(JSON_PATH, "w") as f:
                    json.dump(data, f, indent=2)

    # Final save
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print("Success! Finished repopulating all entries.")

if __name__ == "__main__":
    process_file()
