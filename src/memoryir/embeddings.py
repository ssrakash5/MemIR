"""Embedding wrapper for the eval/ generation harness.

Uses the same local sentence-transformers model as spike/02_embed.py.
This is a placeholder embedding model, not the real study's choice --
see configs/experiment_grid.yaml's embedding_model: TBD. Swap this
module's implementation when that's pinned; callers only depend on
`Embedder.dim` and `Embedder.embed`.
"""
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()
