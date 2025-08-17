import hashlib
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from localknow.config import settings
from localknow.types import Document
from localknow.storage.vectorstore import VectorStore


class AdvancedContentDeduplicator:
    def __init__(self):
        # Use the VectorStore's embedder which is already optimized for Metal
        self.vs = VectorStore("content_dedup")
        self.semantic_embedder = self.vs._embedder
        self.similarity_threshold = settings.similarity_threshold
        self.batch_size = 8  # Optimized for M4's memory architecture

    def generate_semantic_hash(self, embedding: np.ndarray) -> str:
        rounded = np.round(embedding, 3).astype(str)
        joined = ",".join(rounded)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def check_semantic_similarity(self, doc_embedding: np.ndarray, existing_embeddings: List[np.ndarray]) -> bool:
        if not existing_embeddings:
            return False
        sims = cosine_similarity([doc_embedding], existing_embeddings)[0]
        return float(np.max(sims)) >= self.similarity_threshold

    def detect_semantic_duplicates(self, documents: List[Document]) -> List[Document]:
        if not documents:
            return []
            
        unique_docs: List[Document] = []
        existing_embeddings: List[np.ndarray] = []
        processed_hashes = set()
        
        # Process documents in batches to optimize GPU utilization
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i+self.batch_size]
            
            # Extract content for the batch
            batch_contents = [doc.content for doc in batch]
            
            # Generate embeddings for the entire batch at once
            batch_embeddings = self.semantic_embedder.encode(
                batch_contents, 
                normalize_embeddings=True,
                batch_size=self.batch_size,
                show_progress_bar=False
            )
            
            # Process each document in the batch
            for j, doc in enumerate(batch):
                embedding = batch_embeddings[j]
                content_hash = self.generate_semantic_hash(embedding)
                
                if content_hash in processed_hashes:
                    continue
                    
                is_duplicate = self.check_semantic_similarity(embedding, existing_embeddings)
                if not is_duplicate:
                    unique_docs.append(doc)
                    existing_embeddings.append(embedding)
                    processed_hashes.add(content_hash)

        # Persist to vector store for cross-run dedup
        if unique_docs:
            ids = [d.document_id for d in unique_docs]
            embs = [e.tolist() for e in existing_embeddings]
            metas = [d.metadata for d in unique_docs]
            docs = [d.content for d in unique_docs]
            self.vs.upsert(ids, embs, metas, docs)

        return unique_docs 