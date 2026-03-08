import json

with open('/Applications/Development/HackCanada/SDG/synthetic_data.json', 'r') as f:
    data = json.load(f)

empty = 0
for topic in data:
    for subtopic in topic.get('subtopics', []):
        for entry in subtopic.get('entries', []):
            if not entry.get('output'):
                empty += 1
                
print(f"Empty entries remaining: {empty}")
