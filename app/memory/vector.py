from sentence_transformers import SentenceTransformer
import chromadb
import uuid # For unique IDs

class VectorStore:
    def __init__(self):
        # 1. Use PersistentClient to save data to 'db' folder
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.collection = self.client.get_or_create_collection("memory")

    def add(self, texts):
        if not texts:
            return
            
        embeddings = self.embedder.encode(texts).tolist()
        # 2. Use UUIDs or unique strings so you don't overwrite old data
        ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        
        self.collection.add(
            documents=texts, 
            embeddings=embeddings, 
            ids=ids
        )

    def search(self, query, k=5):
        embedding = self.embedder.encode([query]).tolist()
        result = self.collection.query(query_embeddings=embedding, n_results=k)
        
        # Chroma returns a list of lists; flatten and filter
        docs = [d for d in result["documents"][0] if d.strip()]
        return "\n".join(docs) if docs else ""