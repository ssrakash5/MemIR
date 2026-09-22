"""H2: attribution-threshold sweep (0.5, 0.7, 0.85).

DATED DECISION (2026-08-14): attribution_threshold was left in the
frozen design (configs/experiment_grid.yaml's analysis_factors) without
a concrete per-edge score to threshold -- the harness only ever recorded
categorical STRUCTURAL_PARENT/CO_RETRIEVED oracle roles. This script
operationalizes attribution_score as cosine similarity between the
parent and child memory's embedding (both already stored via pgvector
at generation time, computed by the same fixed sentence-transformers
model for every memory regardless of which LLM generated it -- no new
generation needed, no retroactive change to any generated content).

This is an explicit, stated choice, not a silent one: cosine similarity
is a natural stand-in for "how attributable does this edge look to a
similarity-based detector," directly analogous to MemLineage's own
tau x K thresholding mechanism (see docs/paper/related_work.md), but a different
choice (e.g. a trained classifier, or NLI entailment) would also have
been defensible. If this needs revisiting, it is a rubric-level change
requiring a dated deviation entry like any other frozen-design edit.

Usage:
    python eval/compute_h2_metrics.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd

from memoryir import db
from memoryir.metrics import TraceGraph, blast_radius_metrics
from memoryir.scenarios import load_all_scenarios

SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios"
OUT_DIR = REPO_ROOT / "results" / "metrics"
DEPTHS = [1, 2, 3, 4, 5]
THRESHOLDS = [0.5, 0.7, 0.85]


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done'"
    ).fetchall()
    return {r[0]: {"scenario_id": r[1], "model": r[2], "top_k": r[3],
                   "write_fanout": r[4], "derivation_transform": r[5], "seed": r[6]}
            for r in rows}


def load_graphs_with_scores(conn, trace_ids: set[str]) -> dict[str, TraceGraph]:
    graphs: dict[str, dict] = {}
    mem_rows = conn.execute(
        "SELECT trace_id, id, depth, branch, local_id, content_label FROM memories "
        "WHERE trace_id = ANY(%s)", (list(trace_ids),)
    ).fetchall()
    for trace_id, mid, depth, branch, local_id, content_label in mem_rows:
        g = graphs.setdefault(trace_id, {"nodes": {}, "edges": [], "scores": {}, "root_id": None})
        g["nodes"][mid] = {"depth": depth, "branch": branch, "content_label": content_label}
        if branch == "source_fact" and local_id == "P1":
            g["root_id"] = mid

    # Cosine similarity computed directly in Postgres via pgvector's <=>
    # (cosine distance) operator -- avoids pulling 384-dim vectors into
    # Python for ~1.4M edges.
    edge_rows = conn.execute(
        """
        SELECT mi.trace_id, mi.parent_memory_id, mi.child_memory_id, mi.role,
               1 - (p.embedding <=> c.embedding) AS cosine_sim
        FROM memory_influence mi
        JOIN memories p ON p.id = mi.parent_memory_id
        JOIN memories c ON c.id = mi.child_memory_id
        WHERE mi.trace_id = ANY(%s)
        """, (list(trace_ids),)
    ).fetchall()
    for trace_id, pid, cid, role, sim in edge_rows:
        g = graphs[trace_id]
        g["edges"].append((pid, cid, role))
        g["scores"][(pid, cid)] = float(sim)

    return {
        tid: TraceGraph(nodes=g["nodes"], edges=g["edges"], root_id=g["root_id"], edge_scores=g["scores"])
        for tid, g in graphs.items() if g["root_id"] is not None
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(embed_dim=384)

    specs = load_all_scenarios(SCENARIOS_DIR)
    poison_form_by_scenario = {s["scenario_id"]: s["poison_form"] for s in specs}

    meta = load_trace_meta(conn)
    print(f"Loaded metadata for {len(meta)} completed traces.")

    all_trace_ids = list(meta.keys())
    rows = []
    BATCH = 250  # smaller batch: the embedding join is heavier per trace than compute_metrics.py's
    for i in range(0, len(all_trace_ids), BATCH):
        batch_ids = set(all_trace_ids[i:i + BATCH])
        graphs = load_graphs_with_scores(conn, batch_ids)
        for trace_id, graph in graphs.items():
            m = meta[trace_id]
            for depth in DEPTHS:
                for threshold in THRESHOLDS:
                    result = blast_radius_metrics(graph, policy="thresholded", max_depth=depth, threshold=threshold)
                    rows.append({
                        "trace_id": trace_id,
                        "scenario_id": m["scenario_id"],
                        "poison_form": poison_form_by_scenario.get(m["scenario_id"]),
                        "model": m["model"],
                        "top_k": m["top_k"],
                        "write_fanout": m["write_fanout"],
                        "derivation_transform": m["derivation_transform"],
                        "seed": m["seed"],
                        "depth": depth,
                        "attribution_threshold": threshold,
                        **result,
                    })
        print(f"  processed {min(i + BATCH, len(all_trace_ids))}/{len(all_trace_ids)} traces")

    conn.close()

    df = pd.DataFrame(rows)
    raw_path = OUT_DIR / "h2_attribution_threshold_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw H2 results: {raw_path} ({len(df)} rows)")

    valid = df.dropna(subset=["P_BR", "R_BR", "inflation_ratio"])
    per_scenario_condition = (
        valid.groupby(["model", "attribution_threshold", "depth", "scenario_id"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    headline = (
        per_scenario_condition.groupby(["model", "attribution_threshold", "depth"])
        [["P_BR", "R_BR", "inflation_ratio"]].agg(["mean", "std", "count"]).reset_index()
    )
    headline_path = OUT_DIR / "h2_headline_summary.csv"
    headline.to_csv(headline_path, index=False)
    print(f"H2 headline (P_BR/R_BR/inflation vs threshold, per model x depth): {headline_path}")
    print(headline.to_string())


if __name__ == "__main__":
    main()
