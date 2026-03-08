import json
import requests

JSON_PATH = "../synthetic_data.json"
API_URL = "http://localhost:8100/ask"

def process_file():
    target = "Identify the primary legal sources that regulate wetland protection during urban development in Ontario."
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    
    for topic in data:
        for subtopic in topic.get("subtopics", []):
            for entry in subtopic.get("entries", []):
                if entry.get("input") == target:
                    resp = requests.post(API_URL, json={"question": target, "k": 3})
                    answer_data = resp.json()
                    answer = answer_data.get("answer", "")
                    sources = answer_data.get("sources", [])
                    num_sources = answer_data.get("num_sources", 0)
                    
                    formatted_output = f"{answer}\n\n"
                    if num_sources > 0:
                        formatted_output += "Sources:\n"
                        for i, s in enumerate(sources):
                            formatted_output += f"- {s.get('source')} (Type: {s.get('source_type')})\n"
                    
                    entry["output"] = formatted_output
                    print("Updated specific entry.")
                    
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    process_file()
