"""Computes H1's core blast-radius metrics (P_BR, R_BR, inflation_ratio)
over the full labeled corpus, using the validated metrics module
(src/memoryir/metrics.py, see tests/test_metrics.py for the fixture
proof this is correct before it touches real data).

Two policies per docs/preregistration.md's three-layer framework:
  - structural: TRUE_DESCENDANT reachability (STRUCTURAL_PARENT edges only)
  - context_exposure: conservative propagation (STRUCTURAL_PARENT + CO_RETRIEVED)
    -- this is the attribution_threshold=null policy H1 describes.

Attribution-threshold sweep (H2, thresholds 0.5/0.7/0.85) is NOT computed
here -- that requires a defined per-edge attribution/confidence score,
which was never pinned down as part of the frozen design (the harness
records categorical STRUCTURAL_PARENT/CO_RETRIEVED oracle roles, not a
continuous score). That is a separate, explicit decision to make before
H2 can be computed -- flagged, not silently invented.

Per docs/preregistration.md SS5's marginalization rule: average seeds
within each scenario-condition first, then give every scenario_id equal
weight (stratified by poison_form). Reporting hierarchy: pooled-across-
scenarios is primary, poison_form panels are descriptive/exploratory only.

Usage:
    python eval/compute_metrics.py
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
POLICIES = ["structural", "context_exposure"]


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done'"
    ).fetchall()
    return {r[0]: {"scenario_id": r[1], "model": r[2], "top_k": r[3],
                   "write_fanout": r[4], "derivation_transform": r[5], "seed": r[6]}
            for r in rows}


def load_graphs(conn, trace_ids: set[str]) -> dict[str, TraceGraph]:
    """Loads nodes+edges for the given trace_ids, keyed by trace_id."""
    graphs: dict[str, dict] = {}
    mem_rows = conn.execute(
        "SELECT trace_id, id, depth, branch, local_id, content_label FROM memories "
        "WHERE trace_id = ANY(%s)", (list(trace_ids),)
    ).fetchall()
    for trace_id, mid, depth, branch, local_id, content_label in mem_rows:
        g = graphs.setdefault(trace_id, {"nodes": {}, "edges": [], "root_id": None})
        g["nodes"][mid] = {"depth": depth, "branch": branch, "content_label": content_label}
        if branch == "source_fact" and local_id == "P1":
            g["root_id"] = mid

    edge_rows = conn.execute(
        "SELECT trace_id, parent_memory_id, child_memory_id, role FROM memory_influence "
        "WHERE trace_id = ANY(%s)", (list(trace_ids),)
    ).fetchall()
    for trace_id, pid, cid, role in edge_rows:
        graphs[trace_id]["edges"].append((pid, cid, role))

    return {
        tid: TraceGraph(nodes=g["nodes"], edges=g["edges"], root_id=g["root_id"])
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
    BATCH = 500
    for i in range(0, len(all_trace_ids), BATCH):
        batch_ids = set(all_trace_ids[i:i + BATCH])
        graphs = load_graphs(conn, batch_ids)
        for trace_id, graph in graphs.items():
            m = meta[trace_id]
            for depth in DEPTHS:
                for policy in POLICIES:
                    result = blast_radius_metrics(graph, policy=policy, max_depth=depth)
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
                        "policy": policy,
                        **result,
                    })
        print(f"  processed {min(i + BATCH, len(all_trace_ids))}/{len(all_trace_ids)} traces")

    conn.close()

    df = pd.DataFrame(rows)
    raw_path = OUT_DIR / "blast_radius_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw per-trace-per-depth-per-policy results: {raw_path} ({len(df)} rows)")

    # Marginalization per docs/preregistration.md SS5: average seeds
    # within each scenario-condition first...
    valid = df.dropna(subset=["P_BR", "R_BR", "inflation_ratio"])
    per_scenario_condition = (
        valid.groupby(["model", "policy", "depth", "top_k", "write_fanout", "scenario_id"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    # ...then give every scenario_id equal weight (pooled primary estimand).
    pooled = (
        per_scenario_condition.groupby(["model", "policy", "depth", "top_k", "write_fanout"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    pooled_path = OUT_DIR / "h1_pooled_24scenario.csv"
    pooled.to_csv(pooled_path, index=False)
    print(f"H1 pooled-across-24-scenario results (PRIMARY): {pooled_path} ({len(pooled)} rows)")

    # poison_form-stratified panels -- DESCRIPTIVE/EXPLORATORY ONLY (n=6/stratum, see SS4/SS5)
    per_stratum_condition = (
        valid.groupby(["model", "policy", "depth", "top_k", "write_fanout", "poison_form", "scenario_id"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    stratified = (
        per_stratum_condition.groupby(["model", "policy", "depth", "top_k", "write_fanout", "poison_form"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
    )
    stratified_path = OUT_DIR / "h1_by_poison_form_DESCRIPTIVE_ONLY.csv"
    stratified.to_csv(stratified_path, index=False)
    print(f"poison_form-stratified panels (descriptive/exploratory, n=6/stratum): {stratified_path}")

    # Headline summary: pooled P_BR/R_BR/inflation by depth x policy,
    # marginalized fully over top_k/write_fanout too, per model.
    headline = (
        per_scenario_condition.groupby(["model", "policy", "depth", "scenario_id"])
        [["P_BR", "R_BR", "inflation_ratio"]].mean().reset_index()
        .groupby(["model", "policy", "depth"])[["P_BR", "R_BR", "inflation_ratio"]]
        .agg(["mean", "std", "count"]).reset_index()
    )
    headline_path = OUT_DIR / "headline_summary.csv"
    headline.to_csv(headline_path, index=False)
    print(f"\nHeadline summary (fully marginalized, per model x policy x depth): {headline_path}")
    print(headline.to_string())


if __name__ == "__main__":
    main()
