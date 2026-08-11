"""Spike: embedding model returns expected dimension, batch works.

Uses a local sentence-transformers model rather than a hosted embedding
API — no API key was available in this environment, and all-MiniLM-L6-v2
was already cached locally. This is NOT the model choice for the real
study (see NOTE below); it only proves the embedding step of the pipeline
works end to end.
"""
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # weights are already cached; skip network calls

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EXPECTED_DIM = 384


def main() -> None:
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    assert dim == EXPECTED_DIM, f"expected dim {EXPECTED_DIM}, got {dim}"

    single = model.encode("a single memory about the Eiffel Tower")
    assert single.shape == (EXPECTED_DIM,), f"single-encode shape wrong: {single.shape}"

    batch = model.encode(
        [
            "the Eiffel Tower is in Paris",
            "the Eiffel Tower is actually in Berlin",  # deliberately false, for later injection spikes
            "the weather today is sunny",
        ]
    )
    assert batch.shape == (3, EXPECTED_DIM), f"batch-encode shape wrong: {batch.shape}"

    # Sanity check: the two Eiffel Tower sentences (one true, one false) should
    # be closer to each other than either is to the unrelated weather sentence.
    import numpy as np

    def cos(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    sim_paris_berlin = cos(batch[0], batch[1])
    sim_paris_weather = cos(batch[0], batch[2])
    assert sim_paris_berlin > sim_paris_weather, (
        f"expected topically-similar sentences to score higher "
        f"({sim_paris_berlin:.3f} vs {sim_paris_weather:.3f})"
    )

    print(f"GREEN: {MODEL_NAME} loads, dim={dim}, single and batch encode work.")
    print(f"  cos(paris, berlin-false-claim) = {sim_paris_berlin:.3f}")
    print(f"  cos(paris, weather)            = {sim_paris_weather:.3f}")
    print(
        "NOTE: this is a placeholder local model for infra verification only. "
        "The real study's embedding_model is still TBD in "
        "configs/experiment_grid.yaml and docs/preregistration.md — pin a "
        "real choice there, don't silently inherit this one."
    )


if __name__ == "__main__":
    main()
