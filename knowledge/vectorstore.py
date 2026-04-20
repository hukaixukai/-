# new-agent/knowledge/vectorstore.py
"""Vector store for per-subject knowledge bases. Uses FAISS if available, numpy fallback."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from config import SUBJECTS_DIR

# Try FAISS, fall back to numpy
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


class VectorStore:
    """A vector index with associated text chunks and metadata."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.chunks: list[dict] = []  # {"text": str, "source": str, "chunk_id": int}
        self._initialized = False
        # FAISS mode
        self._faiss_index = None
        # Numpy fallback
        self._vectors: np.ndarray | None = None

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """L2-normalize vectors."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return vectors / norms

    def build(self, embeddings: list[list[float]], chunks: list[dict]) -> None:
        """Build the index from embeddings and chunk metadata."""
        if not embeddings:
            return
        self.dimension = len(embeddings[0])
        vectors = np.array(embeddings, dtype=np.float32)
        vectors = self._normalize(vectors)

        if HAS_FAISS:
            self._faiss_index = faiss.IndexFlatIP(self.dimension)
            self._faiss_index.add(vectors)
        else:
            self._vectors = vectors

        self.chunks = list(chunks)
        self._initialized = True

    def query(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """Search for the most similar chunks.

        Returns list of {"text": str, "source": str, "chunk_id": int, "score": float}.
        """
        if not self._initialized or not self.chunks:
            return []
        vec = np.array([query_vector], dtype=np.float32)
        vec = self._normalize(vec)
        k = min(top_k, len(self.chunks))
        if k == 0:
            return []

        if HAS_FAISS and self._faiss_index is not None:
            scores, indices = self._faiss_index.search(vec, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                chunk = dict(self.chunks[idx])
                chunk["score"] = float(score)
                results.append(chunk)
            return results
        else:
            # Numpy fallback: cosine similarity
            if self._vectors is None:
                return []
            sims = self._vectors @ vec.T  # (N, 1)
            sims = sims.flatten()
            top_indices = np.argsort(sims)[::-1][:k]
            results = []
            for idx in top_indices:
                chunk = dict(self.chunks[idx])
                chunk["score"] = float(sims[idx])
                results.append(chunk)
            return results

    def save(self, dir_path: str | Path) -> None:
        """Persist the index and metadata to disk."""
        d = Path(dir_path)
        d.mkdir(parents=True, exist_ok=True)

        if HAS_FAISS and self._faiss_index is not None and self._faiss_index.ntotal > 0:
            faiss.write_index(self._faiss_index, str(d / "index.faiss"))
        elif self._vectors is not None:
            np.save(str(d / "vectors.npy"), self._vectors)

        meta = {"dimension": self.dimension, "chunks": self.chunks, "use_faiss": HAS_FAISS}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, dir_path: str | Path) -> VectorStore:
        """Load a persisted vector store."""
        d = Path(dir_path)
        store = cls()
        meta_path = d / "meta.json"

        if not meta_path.exists():
            return store

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        store.dimension = meta.get("dimension", 1536)
        store.chunks = meta.get("chunks", [])
        use_faiss = meta.get("use_faiss", HAS_FAISS)

        if use_faiss and HAS_FAISS:
            index_path = d / "index.faiss"
            if index_path.exists():
                store._faiss_index = faiss.read_index(str(index_path))
                store._initialized = True
        # Fallback: always try numpy if FAISS path didn't work
        if not store._initialized:
            vec_path = d / "vectors.npy"
            if vec_path.exists():
                store._vectors = np.load(str(vec_path))
                store._initialized = True

        return store

    @property
    def size(self) -> int:
        return len(self.chunks)

    def add(self, embeddings: list[list[float]], chunks: list[dict]) -> None:
        """Add new chunks to an existing index."""
        if not embeddings:
            return
        vectors = np.array(embeddings, dtype=np.float32)
        vectors = self._normalize(vectors)

        if HAS_FAISS:
            if self._faiss_index is None:
                self.dimension = len(embeddings[0])
                self._faiss_index = faiss.IndexFlatIP(self.dimension)
            self._faiss_index.add(vectors)
        else:
            if self._vectors is None:
                self._vectors = vectors
            else:
                self._vectors = np.vstack([self._vectors, vectors])

        self.chunks.extend(chunks)
        self._initialized = True


def get_subject_vector_dir(subject: str) -> Path:
    """Get the vector store directory for a subject."""
    return SUBJECTS_DIR / subject / "vectors"
