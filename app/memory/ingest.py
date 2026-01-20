from pathlib import Path
from app.memory.vector import VectorStore

store = VectorStore()
texts = []
data_path = Path("data")

# 1. Check if directory exists
if not data_path.exists():
    print(f"Error: Directory {data_path} does not exist!")
else:
    for file in data_path.glob("*"):
        print(f"Processing: {file.name}") # Debug: See what's being read
        content = file.read_text().strip()
        
        # Split by double newlines (paragraphs)
        chunks = [c for c in content.split("\n\n") if c.strip()]
        texts.extend(chunks)

# 2. Only add if we actually found text
if texts:
    store.add(texts)
    print("Personal data ingested")
    print("Total docs in memory:", store.collection.count())
else:
    print("No text found to ingest. Check your 'data/personal' folder.")