"""
Hybrid Vector Store with Dense (Embedding) + Sparse (BM25) retrieval.
Production-grade RAG retrieval with re-ranking support.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import uuid
import re
from typing import Optional
from collections import Counter
import math


class BM25:
    """
    Simple BM25 implementation for sparse retrieval.
    Used alongside vector search for hybrid retrieval.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[str] = []
        self.doc_lengths: list[int] = []
        self.avg_doc_length: float = 0
        # term -> number of docs containing it
        self.doc_freqs: dict[str, int] = {}
        # per-document term frequencies
        self.term_freqs: list[dict[str, int]] = []
        self.idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase and split on non-alphanumeric"""
        return re.findall(r'\w+', text.lower())

    def fit(self, documents: list[str]):
        """Build BM25 index from documents"""
        self.documents = documents
        self.term_freqs = []
        self.doc_freqs = Counter()

        for doc in documents:
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))

            # Term frequency for this document
            tf = Counter(tokens)
            self.term_freqs.append(tf)

            # Document frequency (count unique terms per doc)
            for term in set(tokens):
                self.doc_freqs[term] += 1

        self.avg_doc_length = sum(self.doc_lengths) / \
            len(self.doc_lengths) if self.doc_lengths else 0

        # Calculate IDF for all terms
        n_docs = len(documents)
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)

    def search(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        """
        Search for documents matching query.
        Returns list of (doc_index, score) tuples.
        """
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)
        scores = []

        for i, (tf, doc_len) in enumerate(zip(self.term_freqs, self.doc_lengths)):
            score = 0
            for term in query_tokens:
                if term not in tf:
                    continue

                idf = self.idf.get(term, 0)
                term_freq = tf[term]

                # BM25 formula
                numerator = term_freq * (self.k1 + 1)
                denominator = term_freq + self.k1 * \
                    (1 - self.b + self.b * doc_len / self.avg_doc_length)
                score += idf * (numerator / denominator)

            scores.append((i, score))

        # Sort by score descending and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class VectorStore:
    """
    Hybrid retrieval combining:
    1. Dense retrieval (sentence embeddings)
    2. Sparse retrieval (BM25)
    3. Optional re-ranking
    """

    def __init__(self,
                 persist_path: str = "./chroma_db",
                 collection_name: str = "memory",
                 use_hybrid: bool = True):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.collection = self.client.get_or_create_collection(collection_name)
        self.use_hybrid = use_hybrid

        # BM25 index for sparse retrieval
        self.bm25 = BM25()
        self._bm25_docs: list[str] = []
        self._bm25_ids: list[str] = []
        self._bm25_metadata: list[dict] = []

        # Load existing documents for BM25 if any
        self._rebuild_bm25_index()

    def _rebuild_bm25_index(self):
        """Rebuild BM25 index from existing ChromaDB documents"""
        try:
            all_docs = self.collection.get()
            if all_docs["documents"]:
                self._bm25_docs = all_docs["documents"]
                self._bm25_ids = all_docs["ids"]
                self._bm25_metadata = all_docs["metadatas"] or [
                    {}] * len(self._bm25_docs)
                self.bm25.fit(self._bm25_docs)
        except Exception as e:
            print(f"Warning: Could not rebuild BM25 index: {e}")

    def add(self, texts: list[str], metadata_list: Optional[list[dict]] = None):
        """Add documents to both vector store and BM25 index"""
        if not texts:
            return

        embeddings = self.embedder.encode(texts).tolist()
        ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        metadatas = metadata_list or [{"type": "unknown"}] * len(texts)

        # Add to ChromaDB
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        # Update BM25 index
        self._bm25_docs.extend(texts)
        self._bm25_ids.extend(ids)
        self._bm25_metadata.extend(metadatas)
        self.bm25.fit(self._bm25_docs)

    def search(self,
               query: str,
               k: int = 5,
               filter_metadata: Optional[dict] = None,
               hybrid_weight: float = 0.7) -> str:
        """
        Hybrid search combining vector similarity and BM25.

        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Metadata filter (e.g., {"type": "skills"})
            hybrid_weight: Weight for vector search (1-weight for BM25)

        Returns:
            Concatenated relevant documents
        """
        # Dense retrieval (vector search)
        embedding = self.embedder.encode([query]).tolist()

        query_params = {
            "query_embeddings": embedding,
            "n_results": k * 2  # Get more for re-ranking
        }

        if filter_metadata:
            query_params["where"] = filter_metadata

        vector_results = self.collection.query(**query_params)

        # If not using hybrid or no BM25 docs, return vector results only
        if not self.use_hybrid or not self._bm25_docs:
            docs = [d for d in vector_results["documents"][0] if d.strip()]
            return "\n\n".join(docs[:k]) if docs else ""

        # Sparse retrieval (BM25)
        bm25_results = self.bm25.search(query, k=k * 2)

        # Combine and re-rank
        doc_scores: dict[str, float] = {}
        doc_contents: dict[str, str] = {}

        # Score from vector search (normalized)
        if vector_results["documents"][0]:
            vector_docs = vector_results["documents"][0]
            vector_ids = vector_results["ids"][0]
            # ChromaDB distances are L2, convert to similarity
            distances = vector_results.get(
                "distances", [[1.0] * len(vector_docs)])[0]
            max_dist = max(distances) if distances else 1.0

            for doc, doc_id, dist in zip(vector_docs, vector_ids, distances):
                if not doc.strip():
                    continue
                # Convert distance to similarity score (0-1)
                similarity = 1 - (dist / (max_dist + 1e-6))
                doc_scores[doc_id] = hybrid_weight * similarity
                doc_contents[doc_id] = doc

        # Score from BM25 (normalized)
        if bm25_results:
            max_bm25 = max(
                score for _, score in bm25_results) if bm25_results else 1.0

            for idx, score in bm25_results:
                if idx >= len(self._bm25_ids):
                    continue

                doc_id = self._bm25_ids[idx]
                doc = self._bm25_docs[idx]
                metadata = self._bm25_metadata[idx] if idx < len(
                    self._bm25_metadata) else {}

                # Apply metadata filter for BM25 results
                if filter_metadata:
                    if not all(metadata.get(k) == v for k, v in filter_metadata.items()):
                        continue

                if not doc.strip():
                    continue

                # Normalize BM25 score
                norm_score = score / (max_bm25 + 1e-6)

                if doc_id in doc_scores:
                    doc_scores[doc_id] += (1 - hybrid_weight) * norm_score
                else:
                    doc_scores[doc_id] = (1 - hybrid_weight) * norm_score
                    doc_contents[doc_id] = doc

        # Sort by combined score and return top k
        ranked_ids = sorted(doc_scores.keys(),
                            key=lambda x: doc_scores[x], reverse=True)

        results = []
        for doc_id in ranked_ids[:k]:
            if doc_id in doc_contents:
                results.append(doc_contents[doc_id])

        return "\n\n".join(results) if results else ""

    def search_with_scores(self,
                           query: str,
                           k: int = 5,
                           filter_metadata: Optional[dict] = None) -> list[tuple[str, float, dict]]:
        """
        Search and return documents with their scores and metadata.
        Useful for debugging and analysis.

        Returns:
            List of (document, score, metadata) tuples
        """
        embedding = self.embedder.encode([query]).tolist()

        query_params = {
            "query_embeddings": embedding,
            "n_results": k,
            "include": ["documents", "metadatas", "distances"]
        }

        if filter_metadata:
            query_params["where"] = filter_metadata

        results = self.collection.query(**query_params)

        output = []
        if results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [
                {}] * len(docs)
            distances = results["distances"][0] if results["distances"] else [
                0] * len(docs)

            for doc, meta, dist in zip(docs, metadatas, distances):
                if doc.strip():
                    # Convert distance to similarity
                    similarity = 1 / (1 + dist)
                    output.append((doc, similarity, meta))

        return output

    def clear(self):
        """Clear all documents from the store"""
        try:
            self.client.delete_collection("memory")
            self.collection = self.client.get_or_create_collection("memory")
            self._bm25_docs = []
            self._bm25_ids = []
            self._bm25_metadata = []
            self.bm25 = BM25()
            print("✅ Cleared all documents from VectorStore")
        except Exception as e:
            print(f"Warning: Error clearing store: {e}")
