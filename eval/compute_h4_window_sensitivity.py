"""H4 robustness check: depth_aware window sensitivity (1, 2, 3 hops).

The paper's headline H4 result uses depth_aware_window=2 -- a DATED
DECISION (src/memoryir/metrics.py's b_flagged docstring, 2026-08-14)
since the frozen design named "depth_aware" as a policy without
specifying its exact algorithm. An external review of the draft asked
"why 2?" -- a fair question, since the ~30% flagged-object reduction at
window=2 could look like a hand-picked operating point rather than a
real point on a continuous tradeoff.

This script answers that by sweeping depth_aware_window in {1, 2, 3}
at depth=5 (matching Table IV's exact reporting depth), reusing
src/memoryir/metrics.py's b_flagged UNMODIFIED (it already accepts a
depth_aware_window parameter -- no new code in the frozen metrics
module, only a new caller). Full 24-scenario poisoned corpus, all 3
models, all 5 seeds -- same scope as the original H4 computation, no
new generation.

Usage:
    python eval/compute_h4_window_sensitivity.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd

from memoryir import db
from memoryir.metrics import TraceGraph, b_true, b_flagged
from memoryir.scenarios import load_all_scenarios

WINDOWS = [1, 2, 3]
DEPTH = 5
OUT_DIR = REPO_ROOT / "results" / "metrics"


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done' AND scenario_id NOT LIKE 'RD%' "
        "AND scenario_id NOT LIKE 'clean_control%'"
    ).fetchall()
    return {r[0]: {"scenario_id": r[1], "model": r[2], "top_k": r[3],
                   "write_fanout": r[4], "derivation_transform": r[5], "seed": r[6]}
            for r in rows}


def load_graphs(conn, trace_ids: set[str]) -> dict[str, TraceGraph]:
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

    specs = load_all_scenarios(REPO_ROOT / "configs" / "scenarios")
    poison_form_by_scenario = {s["scenario_id"]: s["poison_form"] for s in specs}

    meta = load_trace_meta(conn)
    print(f"Loaded metadata for {len(meta)} completed traces (24-scenario poisoned corpus only).")

    all_trace_ids = list(meta.keys())
    rows = []
    BATCH = 500
    for i in range(0, len(all_trace_ids), BATCH):
        batch_ids = set(all_trace_ids[i:i + BATCH])
        graphs = load_graphs(conn, batch_ids)
        for trace_id, graph in graphs.items():
            m = meta[trace_id]
            bt = b_true(graph, max_depth=DEPTH)
            for window in WINDOWS:
                bf = b_flagged(graph, policy="depth_aware", max_depth=DEPTH, depth_aware_window=window)
                missed = bt - bf
                rows.append({
                    "trace_id": trace_id, "scenario_id": m["scenario_id"],
                    "poison_form": poison_form_by_scenario.get(m["scenario_id"]),
                    "model": m["model"], "seed": m["seed"],
                    "depth_aware_window": window,
                    "b_true_n": len(bt), "b_flagged_n": len(bf),
                    "missed_contaminated_n": len(missed),
                })
        print(f"  processed {min(i + BATCH, len(all_trace_ids))}/{len(all_trace_ids)} traces")

    conn.close()
    df = pd.DataFrame(rows)
    raw_path = OUT_DIR / "h4_window_sensitivity_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw window-sensitivity results: {raw_path} ({len(df)} rows)")

    # Marginalize within scenario (average across models x seeds), per
    # docs/preregistration.md SS5's rule, then per (window, model) for the
    # paper's headline table -- scenario_id as the unit, n=24.
    per_scenario = (
        df.groupby(["depth_aware_window", "model", "scenario_id"])
        [["b_flagged_n", "missed_contaminated_n"]].mean().reset_index()
    )
    headline_by_model = (
        per_scenario.groupby(["depth_aware_window", "model"])
        [["b_flagged_n", "missed_contaminated_n"]].agg(["mean", "std", "count"]).reset_index()
    )
    headline_path = OUT_DIR / "h4_window_sensitivity_by_model.csv"
    headline_by_model.to_csv(headline_path, index=False)

    pooled = (
        per_scenario.groupby(["depth_aware_window"])
        [["b_flagged_n", "missed_contaminated_n"]].agg(["mean", "std", "count"]).reset_index()
    )
    pooled_path = OUT_DIR / "h4_window_sensitivity_pooled.csv"
    pooled.to_csv(pooled_path, index=False)

    print(f"\nWindow-sensitivity headline (depth=5, per model): {headline_path}")
    print(headline_by_model.to_string())
    print(f"\nWindow-sensitivity headline (depth=5, pooled across models): {pooled_path}")
    print(pooled.to_string())


if __name__ == "__main__":
    main()
