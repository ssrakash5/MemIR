"""False-positive baseline on the 6 clean_control scenarios (added
2026-08-15, explicit user decision) -- week3.md/week4.md's "measure
false-positive behavior" requirement the original 24-scenario design
lacked.

Two distinct false-positive signals, reported separately since they
test different components:
  1. LABELER false positives: does the content-level labeler ever
     assign CARRIES/REFERENCES to a derived memory in a scenario with
     no adversarial content anywhere? (tests the labeler, not the
     propagation policy)
  2. PROPAGATION false positives: how many objects does each detection
     policy (structural/context_exposure/flat_transitive/depth_aware)
     flag when run "as if" the benign P1 were a compromised root?
     (tests the containment mechanism's over-quarantine behavior on a
     genuinely clean trace -- since B_true is ~0 here by construction,
     every flagged object is a false positive by definition)

Usage:
    python eval/compute_clean_control_metrics.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd

from memoryir import db
from memoryir.metrics import TraceGraph, b_flagged, b_true

POLICIES = ["structural", "context_exposure", "flat_transitive", "depth_aware"]
DEPTHS = [1, 2, 3, 4, 5]


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done' AND scenario_id LIKE 'clean_control%'"
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
    OUT_DIR = REPO_ROOT / "results" / "metrics"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(embed_dim=384)

    meta = load_trace_meta(conn)
    print(f"Loaded metadata for {len(meta)} completed clean_control traces.")

    # --- Signal 1: labeler false positives ---
    label_rows = conn.execute(
        """
        SELECT m.content_label, count(*)
        FROM memories m
        WHERE m.trace_id = ANY(%s) AND m.branch IN ('child_1','child_2','child_3')
        GROUP BY m.content_label
        """, (list(meta.keys()),)
    ).fetchall()
    label_counts = dict(label_rows)
    total_derived = sum(label_counts.values())
    print(f"\n=== Labeler false-positive check (clean_control corpus, {total_derived} derived memories) ===")
    for label, count in sorted(label_counts.items(), key=lambda x: str(x[0])):
        pct = 100 * count / total_derived if total_derived else 0
        print(f"  {label}: {count} ({pct:.3f}%)")
    fp_rate = (label_counts.get("CARRIES", 0) + label_counts.get("REFERENCES", 0)) / total_derived if total_derived else 0
    print(f"  Labeler false-positive rate (CARRIES+REFERENCES / total): {fp_rate:.4%}")

    # --- Signal 2: propagation false positives ---
    all_trace_ids = list(meta.keys())
    rows = []
    BATCH = 500
    for i in range(0, len(all_trace_ids), BATCH):
        batch_ids = set(all_trace_ids[i:i + BATCH])
        graphs = load_graphs(conn, batch_ids)
        for trace_id, graph in graphs.items():
            m = meta[trace_id]
            for depth in DEPTHS:
                bt = b_true(graph, max_depth=depth)  # expected ~0 (no real poison)
                for policy in POLICIES:
                    bf = b_flagged(graph, policy=policy, max_depth=depth)
                    rows.append({
                        "trace_id": trace_id, "scenario_id": m["scenario_id"],
                        "model": m["model"], "derivation_transform": m["derivation_transform"],
                        "top_k": m["top_k"], "write_fanout": m["write_fanout"], "seed": m["seed"],
                        "depth": depth, "policy": policy,
                        "b_true_n": len(bt), "b_flagged_n": len(bf),
                    })
    conn.close()

    df = pd.DataFrame(rows)
    raw_path = OUT_DIR / "clean_control_false_positive_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw propagation false-positive results: {raw_path} ({len(df)} rows)")

    print(f"\n=== B_true sanity check (should be ~0 everywhere -- if not, a 'clean' "
          f"scenario leaked real contamination) ===")
    print(f"  Non-zero B_true count: {(df['b_true_n'] > 0).sum()} / {len(df)} rows")
    if (df["b_true_n"] > 0).any():
        print("  WARNING: some clean_control traces have non-zero B_true -- inspect before trusting this baseline.")

    summary = df.groupby(["model", "policy", "depth"])["b_flagged_n"].agg(["mean", "std", "max"]).reset_index()
    summary_path = OUT_DIR / "clean_control_false_positive.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nPropagation false-positive summary (avg objects flagged on genuinely clean traces): {summary_path}")
    print(summary.to_string())


if __name__ == "__main__":
    main()
