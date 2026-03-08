import requests
import sys

resp = requests.post("http://localhost:8100/ask", json={"question": "Identify the primary legal sources that regulate wetland protection during urban development in Ontario.", "k": 3})
try:
    print(resp.json()["answer"])
except Exception as e:
    print("Error:", e, resp.text)
