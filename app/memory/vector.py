from sentence_transformers import SentenceTransformer
import chromadb

class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        # Force CPU
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.collection = self.client.get_or_create_collection("memory")

    def add(self, texts):
        embeddings = self.embedder.encode(texts).tolist()
        ids = [str(i) for i in range(len(texts))]
        self.collection.add(documents=texts, embeddings=embeddings, ids=ids)

    def search(self, query, k=5):
        embedding = self.embedder.encode([query]).tolist()
        result = self.collection.query(query_embeddings=embedding, n_results=k)
        docs = [d for d in result["documents"][0] if d.strip()]
        if not docs:
            return ""  # will trigger "I don't know"
        return "\n".join(docs)

