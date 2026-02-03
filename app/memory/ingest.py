from pathlib import Path
from app.memory.vector import VectorStore
import chromadb

# Clear existing data first
client = chromadb.PersistentClient(path="./chroma_db")
try:
    client.delete_collection("memory")
    print("✅ Cleared old data from ChromaDB")
except Exception as e:
    print(f"No existing collection to clear: {e}")

store = VectorStore()
texts = []
all_metadata = []

data_path = Path("data")

# 1. Check if directory exists
if not data_path.exists():
    print(f"Error: Directory {data_path} does not exist!")
else:
    for file in data_path.glob("*"):
        content = file.read_text().strip()
        chunks = [c for c in content.split("\n\n") if c.strip()]

        # Determine metadata based on filename
        if file.name == "experience.md":
            metadata = [{"type": "professional_experience",
                         "source": file.name}] * len(chunks)
        elif file.name == "projects.md":
            metadata = [{"type": "personal_projects",
                         "source": file.name}] * len(chunks)
        elif file.name == "education.md":
            metadata = [{"type": "education",
                         "source": file.name}] * len(chunks)
        elif file.name == "skills.md":
            metadata = [{"type": "skills", "source": file.name}] * len(chunks)
        else:
            metadata = [{"type": "general", "source": file.name}] * len(chunks)

        texts.extend(chunks)
        all_metadata.extend(metadata)


# 2. Only add if we actually found text
if texts:
    store.add(texts, all_metadata)
    print("Personal data ingested")
    print("Total docs in memory:", store.collection.count())
else:
    print("No text found to ingest. Check your 'data/personal' folder.")
