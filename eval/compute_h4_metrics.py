"""H4: containment comparison, flat_transitive vs depth_aware, on BOTH
over-quarantine cost (C_regen) and missed contamination -- per
docs/preregistration.md, not a one-sided "conservative taint explodes"
demonstration.

C_regen = count of distinct depths (1..max_depth) containing at least
one flagged node -- since each depth in a trace is one generating run
(shared retrieval per run, per configs/experiment_grid.yaml), this
matches the frozen definition: "count of unique generating runs that
must be replayed... one run producing 3 exposed memories is 1 replay."

Usage:
    python eval/compute_h4_metrics.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd

from memoryir import db
from memoryir.metrics import TraceGraph, b_true, b_flagged
from memoryir.scenarios import load_all_scenarios

POLICIES = ["flat_transitive", "depth_aware"]
DEPTHS = [1, 2, 3, 4, 5]


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done'"
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


def c_regen(graph: TraceGraph, flagged: set[int]) -> int:
    depths_touched = {graph.nodes[nid]["depth"] for nid in flagged}
    return len(depths_touched)


def main() -> None:
    OUT_DIR = REPO_ROOT / "results" / "metrics"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(embed_dim=384)

    specs = load_all_scenarios(REPO_ROOT / "configs" / "scenarios")
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
                bt = b_true(graph, max_depth=depth)
                for policy in POLICIES:
                    bf = b_flagged(graph, policy=policy, max_depth=depth)
                    missed = bt - bf
                    rows.append({
                        "trace_id": trace_id, "scenario_id": m["scenario_id"],
                        "poison_form": poison_form_by_scenario.get(m["scenario_id"]),
                        "model": m["model"], "derivation_transform": m["derivation_transform"],
                        "top_k": m["top_k"], "write_fanout": m["write_fanout"], "seed": m["seed"],
                        "depth": depth, "policy": policy,
                        "b_true_n": len(bt), "b_flagged_n": len(bf),
                        "missed_contaminated_n": len(missed),
                        "c_regen": c_regen(graph, bf),
                        "c_regen_oracle": c_regen(graph, bt),  # minimum possible replay cost
                    })
        print(f"  processed {min(i + BATCH, len(all_trace_ids))}/{len(all_trace_ids)} traces")

    conn.close()
    df = pd.DataFrame(rows)
    raw_path = OUT_DIR / "h4_containment_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw H4 results: {raw_path} ({len(df)} rows)")

    df["regen_overhead"] = df.apply(
        lambda r: (r["c_regen"] / r["c_regen_oracle"]) if r["c_regen_oracle"] > 0 else None, axis=1
    )

    per_scenario_condition = (
        df.groupby(["model", "policy", "depth", "scenario_id"])
        [["c_regen", "missed_contaminated_n", "regen_overhead"]].mean().reset_index()
    )
    headline = (
        per_scenario_condition.groupby(["model", "policy", "depth"])
        [["c_regen", "missed_contaminated_n", "regen_overhead"]].agg(["mean", "std"]).reset_index()
    )
    headline_path = OUT_DIR / "h4_headline_summary.csv"
    headline.to_csv(headline_path, index=False)
    print(f"H4 headline (C_regen, missed contamination, Regeneration Overhead): {headline_path}")
    print(headline.to_string())


if __name__ == "__main__":
    main()
