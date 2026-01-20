from pathlib import Path
from app.memory.vector import VectorStore

store = VectorStore()
texts = []

for file in Path("data/personal").glob("*"):
    content = file.read_text().strip()
    # Split by double newlines (paragraphs)
    chunks = [c for c in content.split("\n\n") if c.strip()]
    texts.extend(chunks)


store.add(texts)
print("Personal data ingested")
print("Total docs in memory:", store.collection.count())
