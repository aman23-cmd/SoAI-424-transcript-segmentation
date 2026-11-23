"""Sentence embedding wrappers."""
import zlib
import numpy as np


class Embedder:
    """all-MiniLM-L6-v2 (or another sentence-transformers model); outputs unit-length vectors."""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        return np.asarray(self.model.encode(list(texts), normalize_embeddings=True))


class HashingEmbedder:
    """Deterministic bag-of-words embedder. ONLY for smoke tests, never for reported results."""

    def __init__(self, dim=256):
        self.dim = dim

    def encode(self, texts):
        out = np.zeros((len(texts), self.dim))
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, zlib.crc32(w.encode()) % self.dim] += 1.0
        norm = np.linalg.norm(out, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        return out / norm
