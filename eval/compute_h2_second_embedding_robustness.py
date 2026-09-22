"""H2 robustness check: does the precision/recall attribution frontier
survive under a materially different embedding model?

The paper's headline H2 result thresholds cosine similarity from
all-MiniLM-L6-v2 -- explicitly documented (src/memoryir/embeddings.py)
as a placeholder pinned for the main run, not validated against any
other embedding space. An external review flagged the obvious
criticism: "the attribution frontier may be an artifact of one
embedding space."

This script answers that WITHOUT touching the frozen main-run pgvector
embeddings or rerunning any generation: it re-embeds memory CONTENT
(already stored, unmodified) with a second, architecturally different
model (all-mpnet-base-v2 -- MPNet, not MiniLM; different training
mixture; 768-dim vs 384-dim), computes new cosine similarities in
Python, and re-runs the exact same blast_radius_metrics(policy=
"thresholded", ...) from src/memoryir/metrics.py -- no metric
reimplementation.

Scope, stated explicitly (this is a targeted robustness check, not a
full H2 re-run): gpt-4o-mini, seed=0, all 24 poisoned scenarios, depths
1-5. One model/seed keeps re-embedding tractable locally (~25k distinct
memory nodes) while still covering the full scenario design (n=24,
all 4 poison_forms, all top_k/write_fanout/transform cells). Absolute
threshold values are NOT expected to match the MiniLM run (different
embedding spaces have different similarity distributions) -- thresholds
here are chosen from this run's own similarity distribution. What is
being tested is whether P_BR/R_BR still trade off monotonically as the
threshold increases, not whether the same threshold produces the same
numbers.

Usage:
    python eval/compute_h2_second_embedding_robustness.py
"""
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import os
os.environ.setdefault("HF_HUB_OFFLINE", "0")
import requests
requests.packages.urllib3.disable_warnings()
_orig_request = requests.Session.request
def _patched(self, *a, **kw):
    kw.setdefault("verify", False)
    return _orig_request(self, *a, **kw)
requests.Session.request = _patched

import numpy as np
import pandas as pd

from memoryir import db
from memoryir.metrics import TraceGraph, blast_radius_metrics
from memoryir.scenarios import load_all_scenarios

SECOND_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
OUT_DIR = REPO_ROOT / "results" / "metrics"
DEPTHS = [1, 2, 3, 4, 5]
SCOPE_MODEL = "gpt-4o-mini"
SCOPE_SEED = 0


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done' AND model=%s AND seed=%s "
        "AND scenario_id NOT LIKE 'RD%%' AND scenario_id NOT LIKE 'clean_control%%'",
        (SCOPE_MODEL, SCOPE_SEED),
    ).fetchall()
    return {r[0]: {"scenario_id": r[1], "model": r[2], "top_k": r[3],
                   "write_fanout": r[4], "derivation_transform": r[5], "seed": r[6]}
            for r in rows}


def load_nodes_edges_content(conn, trace_ids: set[str]):
    """Returns (per-trace node/edge structure, {memory_id: content})."""
    graphs: dict[str, dict] = {}
    content_by_id: dict[int, str] = {}
    mem_rows = conn.execute(
        "SELECT trace_id, id, depth, branch, local_id, content_label, content FROM memories "
        "WHERE trace_id = ANY(%s)", (list(trace_ids),)
    ).fetchall()
    for trace_id, mid, depth, branch, local_id, content_label, content in mem_rows:
        g = graphs.setdefault(trace_id, {"nodes": {}, "edges": [], "root_id": None})
        g["nodes"][mid] = {"depth": depth, "branch": branch, "content_label": content_label}
        content_by_id[mid] = content or ""
        if branch == "source_fact" and local_id == "P1":
            g["root_id"] = mid

    edge_rows = conn.execute(
        "SELECT trace_id, parent_memory_id, child_memory_id, role FROM memory_influence "
        "WHERE trace_id = ANY(%s)", (list(trace_ids),)
    ).fetchall()
    for trace_id, pid, cid, role in edge_rows:
        graphs[trace_id]["edges"].append((pid, cid, role))

    return graphs, content_by_id


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(embed_dim=384)

    specs = load_all_scenarios(REPO_ROOT / "configs" / "scenarios")
    poison_form_by_scenario = {s["scenario_id"]: s["poison_form"] for s in specs}

    meta = load_trace_meta(conn)
    print(f"Loaded metadata for {len(meta)} completed traces "
          f"(scope: model={SCOPE_MODEL}, seed={SCOPE_SEED}, 24 poisoned scenarios only).")
    all_trace_ids = list(meta.keys())

    print("Loading nodes/edges/content for all scoped traces...")
    graphs_raw, content_by_id = load_nodes_edges_content(conn, set(all_trace_ids))
    conn.close()
    print(f"  {len(graphs_raw)} traces, {len(content_by_id)} distinct memory nodes to embed.")

    print(f"Loading second embedding model: {SECOND_MODEL_NAME} ...")
    from sentence_transformers import SentenceTransformer
    t0 = time.time()
    model = SentenceTransformer(SECOND_MODEL_NAME)
    print(f"  loaded in {time.time() - t0:.1f}s, dim={model.get_sentence_embedding_dimension()}")

    ids = list(content_by_id.keys())
    texts = [content_by_id[i] for i in ids]
    print(f"Encoding {len(texts)} memory contents...")
    t0 = time.time()
    embs = model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
    # L2-normalize once so cosine similarity is a plain dot product.
    embs = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    emb_by_id = {i: e for i, e in zip(ids, embs)}
    print(f"  encoded in {time.time() - t0:.1f}s")

    # Inspect the new similarity distribution before picking thresholds --
    # different embedding spaces have different scales, so the MiniLM run's
    # 0.5/0.7/0.85 have no privileged meaning here.
    sample_sims = []
    rng = np.random.default_rng(0)
    sample_trace_ids = rng.choice(list(graphs_raw.keys()), size=min(200, len(graphs_raw)), replace=False)
    for tid in sample_trace_ids:
        for pid, cid, role in graphs_raw[tid]["edges"]:
            sample_sims.append(float(np.dot(emb_by_id[pid], emb_by_id[cid])))
    sample_sims = np.array(sample_sims)
    print(f"\nSecond-embedding cosine-similarity distribution over a {len(sample_sims)}-edge sample:")
    print(f"  min={sample_sims.min():.3f} p10={np.percentile(sample_sims, 10):.3f} "
          f"p25={np.percentile(sample_sims, 25):.3f} median={np.median(sample_sims):.3f} "
          f"p75={np.percentile(sample_sims, 75):.3f} p90={np.percentile(sample_sims, 90):.3f} "
          f"max={sample_sims.max():.3f}")

    # Thresholds chosen from this run's own distribution (roughly p25/median/p75),
    # rounded to readable values -- NOT the MiniLM run's 0.5/0.7/0.85.
    thresholds = sorted({round(float(np.percentile(sample_sims, q)), 2) for q in (25, 50, 75)})
    if len(thresholds) < 3:
        thresholds = [round(float(np.percentile(sample_sims, q)), 2) for q in (20, 50, 80)]
    print(f"Using thresholds (own-distribution quantiles): {thresholds}")

    rows = []
    for trace_id, g in graphs_raw.items():
        edge_scores = {(pid, cid): float(np.dot(emb_by_id[pid], emb_by_id[cid]))
                        for pid, cid, role in g["edges"]}
        graph = TraceGraph(nodes=g["nodes"], edges=g["edges"], root_id=g["root_id"], edge_scores=edge_scores)
        if graph.root_id is None:
            continue
        m = meta[trace_id]
        for depth in DEPTHS:
            for threshold in thresholds:
                result = blast_radius_metrics(graph, policy="thresholded", max_depth=depth, threshold=threshold)
                rows.append({
                    "trace_id": trace_id, "scenario_id": m["scenario_id"],
                    "poison_form": poison_form_by_scenario.get(m["scenario_id"]),
                    "model": m["model"], "top_k": m["top_k"], "write_fanout": m["write_fanout"],
                    "derivation_transform": m["derivation_transform"], "seed": m["seed"],
                    "depth": depth, "attribution_threshold": threshold,
                    "embedding_model": SECOND_MODEL_NAME,
                    **result,
                })

    df = pd.DataFrame(rows)
    raw_path = OUT_DIR / "h2_second_embedding_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw second-embedding H2 results: {raw_path} ({len(df)} rows)")

    valid = df.dropna(subset=["P_BR", "R_BR", "inflation_ratio"])
    per_scenario = (
        valid.groupby(["attribution_threshold", "depth", "scenario_id"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    headline = (
        per_scenario.groupby(["attribution_threshold", "depth"])
        [["P_BR", "R_BR", "inflation_ratio"]].agg(["mean", "std", "count"]).reset_index()
    )
    headline_path = OUT_DIR / "h2_second_embedding_headline.csv"
    headline.to_csv(headline_path, index=False)
    print(f"\nSecond-embedding H2 headline (P_BR/R_BR/inflation vs threshold, pooled over gpt-4o-mini/"
          f"seed0/24 scenarios): {headline_path}")
    print(headline.to_string())

    print("\n=== depth=5 only (matches main Table III's reporting depth) ===")
    print(headline[headline["depth"] == 5].to_string())


if __name__ == "__main__":
    main()
