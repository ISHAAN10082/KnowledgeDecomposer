import chromadb
import torch
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from intellidoc.config import settings


class VectorStore:
    def __init__(self, collection_name: str = "content_dedup"):
        self.client = chromadb.PersistentClient(path=settings.chroma_db_dir)
        self.collection = self.client.get_or_create_collection(collection_name)
        
        # Use MPS (Metal Performance Shaders) if available for GPU acceleration
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Using device for embeddings: {device}")
        self._embedder = SentenceTransformer("all-MiniLM-L6-v2", device=device)

    def embed(self, texts, batch_size=32):
        """Generate embeddings with batching for memory efficiency"""
        return self._embedder.encode(
            texts, 
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False
        ).tolist()

    def upsert(self, ids, embeddings, metadatas, documents):
        self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def query(self, query_embeddings, n_results: int = 5):
        return self.collection.query(query_embeddings=query_embeddings, n_results=n_results) 