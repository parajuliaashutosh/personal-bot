from sentence_transformers import SentenceTransformer
import chromadb
import uuid # For unique IDs

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.collection = self.client.get_or_create_collection("memory")

    def add(self, texts, metadata_list=None):
        if not texts:
            return
            
        embeddings = self.embedder.encode(texts).tolist()
        ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        
        self.collection.add(
            documents=texts, 
            embeddings=embeddings, 
            ids=ids,
            metadatas=metadata_list or [{"type": "unknown"}] * len(texts)
        )

    def search(self, query, k=5, filter_metadata=None):
        embedding = self.embedder.encode([query]).tolist()
        
        query_params = {
            "query_embeddings": embedding,
            "n_results": k
        }
        
        if filter_metadata:
            query_params["where"] = filter_metadata
        
        result = self.collection.query(**query_params)
        docs = [d for d in result["documents"][0] if d.strip()]
        return "\n".join(docs) if docs else ""