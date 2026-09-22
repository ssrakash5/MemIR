"""Summary metrics for the real-document validation slice
(configs/scenarios/real_documents/RD01..RD20.yaml, 240 traces, 2400
labeled memories -- generated/labeled 2026-09-22 via
eval/run_real_document_validation.py and
eval/label_real_document_validation.py).

Reuses the exact same validated metrics module (src/memoryir/metrics.py:
TraceGraph, b_true, b_flagged, blast_radius_metrics) the synthetic
corpus's H1/H2/H3/H4 scripts use -- no reimplementation, no new metric
definitions. The only new code here is the RD-specific scenario lookup
(poison_form + marker_type, the latter not present in the synthetic
corpus at all) and the aggregation/output shape the user asked for.

Sampling unit: the 20 RD scenarios (RD01-RD20), NOT the 240 traces --
mirrors docs/preregistration.md SS5's marginalization rule (average
seeds/conditions within each scenario first, then treat every scenario
as one equally-weighted unit). This slice has only 1 seed, so "averaging
within scenario" here means averaging across (model, top_k, transform)
conditions unless a breakdown table explicitly holds one of those fixed.

Per the user's explicit instruction (2026-09-22): this is a DESCRIPTIVE
validation slice, not a hypothesis-test corpus. No Wilcoxon significance
tests are computed here (unlike the synthetic corpus's bootstrap_h1.py
etc.) -- only means and percentile bootstrap CIs, stratified by
poison_form (5/stratum, matching the frozen 5/5/5/5 allocation) the same
way the synthetic corpus's bootstrap stratifies by poison_form.

Usage:
    python eval/compute_real_document_metrics.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import pandas as pd

from memoryir import db
from memoryir.metrics import TraceGraph, b_flagged, b_true, blast_radius_metrics
from memoryir.scenarios import extract_markers, load_scenario

RD_SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios" / "real_documents"
OUT_DIR = REPO_ROOT / "results" / "real_document_validation"
DEPTHS = [1, 2, 3, 4, 5]
POLICIES = ["structural", "context_exposure", "flat_transitive", "depth_aware"]
THRESHOLDS = [0.5, 0.7]
N_BOOT = 10_000
RNG_SEED = 0

# Marker type per scenario -- documented in each RDxx/provenance.yaml's
# marker_type field (real_documents/RDxx/provenance.yaml), reproduced here
# as the single source of truth for THIS script since the frozen scenario
# YAML schema (shared with the synthetic corpus) has no marker_type field
# of its own. Matches real_documents/VALIDATION_CHECKLIST.md's frozen
# crossed allocation table exactly -- verified programmatically at the end
# of this file's __main__ guard (5/5/5/5), not just asserted here.
MARKER_TYPE_BY_SCENARIO = {
    "RD01_nist_ai_rmf_govern": "email_domain",
    "RD02_aws_ecs_anywhere": "invented_id",
    "RD03_nist_genai_infosec": "numeric_time",
    "RD04_nist_csf_tiers": "natural_language",
    "RD05_cisa_ztmm_optimal": "invented_id",
    "RD06_owasp_copilot_calendar": "numeric_time",
    "RD07_nist_tiers_coordinating_council": "natural_language",
    "RD08_ftc_twitter_compliance": "email_domain",
    "RD09_nist_sp1308_scoping": "numeric_time",
    "RD10_fda_image_compression_lib": "natural_language",
    "RD11_aws_dr_runbook": "email_domain",
    "RD12_azure_recovery_tier_code": "invented_id",
    "RD13_azure_fma_signoff": "natural_language",
    "RD14_azure_workload_identity_notify": "email_domain",
    # NOTE: the YAML file is named RD15_aws_ar17_quota.yaml (renamed after
    # the scenario's marker was changed from "REL01-BP07" to "AR-17" to
    # fix a marker-leak bug, see its provenance.yaml), but the
    # scenario_id FIELD inside that file was never updated to match --
    # and 240-run generation/labeling already ran under this OLD id, so
    # fixing the field now would orphan real, paid-for API data. Left as
    # a known, documented inconsistency (filename != scenario_id for
    # RD15 only) rather than silently regenerating.
    "RD15_aws_rel01bp07_quota": "invented_id",
    "RD16_fda_isao_grace_period": "numeric_time",
    "RD17_irs_pub1_objections_email": "email_domain",
    "RD18_irs_pub5_hsa_appeal": "invented_id",
    "RD19_irs_pub594_protest_deadline": "numeric_time",
    "RD20_irs_pub1660_ex_parte_cert": "natural_language",
}


def load_rd_specs() -> list[dict]:
    return [load_scenario(p) for p in sorted(RD_SCENARIOS_DIR.glob("*.yaml"))]


def load_trace_meta(conn) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT trace_id, scenario_id, model, top_k, write_fanout, derivation_transform, seed "
        "FROM sweep_runs WHERE status='done' AND scenario_id LIKE 'RD%'"
    ).fetchall()
    return {r[0]: {"scenario_id": r[1], "model": r[2], "top_k": r[3],
                   "write_fanout": r[4], "derivation_transform": r[5], "seed": r[6]}
            for r in rows}


def load_graphs_with_scores_and_content(conn, trace_ids: set[str]):
    graphs: dict[str, dict] = {}
    mem_rows = conn.execute(
        "SELECT trace_id, id, depth, branch, local_id, content_label, content FROM memories "
        "WHERE trace_id = ANY(%s)", (list(trace_ids),)
    ).fetchall()
    for trace_id, mid, depth, branch, local_id, content_label, content in mem_rows:
        g = graphs.setdefault(trace_id, {"nodes": {}, "edges": [], "scores": {}, "content": {}, "root_id": None})
        g["nodes"][mid] = {"depth": depth, "branch": branch, "content_label": content_label}
        g["content"][mid] = content
        if branch == "source_fact" and local_id == "P1":
            g["root_id"] = mid

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

    out = {}
    for tid, g in graphs.items():
        if g["root_id"] is None:
            continue
        out[tid] = (
            TraceGraph(nodes=g["nodes"], edges=g["edges"], root_id=g["root_id"], edge_scores=g["scores"]),
            g["content"],
        )
    return out


def bootstrap_ci(values: np.ndarray, strata: np.ndarray, n_boot: int, rng: np.random.Generator):
    unique_strata = np.unique(strata)
    idx_by_stratum = [np.where(strata == s)[0] for s in unique_strata]
    boot_means = np.empty(n_boot)
    for b in range(n_boot):
        resampled = np.concatenate([rng.choice(idx, size=len(idx), replace=True) for idx in idx_by_stratum])
        boot_means[b] = values[resampled].mean()
    return float(values.mean()), float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(embed_dim=384)

    specs = load_rd_specs()
    assert len(specs) == 20, f"expected 20 RD scenarios, found {len(specs)}"
    poison_form_by_scenario = {s["scenario_id"]: s["poison_form"] for s in specs}
    markers_by_scenario = {s["scenario_id"]: extract_markers(s) for s in specs}

    # Sanity: MARKER_TYPE_BY_SCENARIO and poison_form_by_scenario both 5/5/5/5.
    from collections import Counter
    pf_counts = Counter(poison_form_by_scenario.values())
    mk_counts = Counter(MARKER_TYPE_BY_SCENARIO.values())
    assert set(pf_counts.values()) == {5}, f"poison_form not 5/5/5/5: {pf_counts}"
    assert set(mk_counts.values()) == {5}, f"marker_type not 5/5/5/5: {mk_counts}"
    assert set(MARKER_TYPE_BY_SCENARIO) == set(poison_form_by_scenario), "marker_type map missing/extra scenario_ids"

    meta = load_trace_meta(conn)
    print(f"Loaded metadata for {len(meta)} completed RD traces (expect 240).")
    all_trace_ids = list(meta.keys())

    # ---------- Pass 1: H1/H2/H4-style blast-radius rows (one row per trace x depth x policy/threshold) ----------
    br_rows = []
    h3_rows = []
    child2_rows = []
    BATCH = 60
    for i in range(0, len(all_trace_ids), BATCH):
        batch_ids = set(all_trace_ids[i:i + BATCH])
        graphs = load_graphs_with_scores_and_content(conn, batch_ids)
        for trace_id, (graph, content) in graphs.items():
            m = meta[trace_id]
            sid = m["scenario_id"]
            structural_reachable_d5 = b_flagged(graph, policy="structural", max_depth=5)
            markers = markers_by_scenario.get(sid, set())

            for depth in DEPTHS:
                bt = b_true(graph, max_depth=depth)
                for policy in POLICIES:
                    result = blast_radius_metrics(graph, policy=policy, max_depth=depth)
                    bf = b_flagged(graph, policy=policy, max_depth=depth)
                    br_rows.append({
                        "trace_id": trace_id, "scenario_id": sid,
                        "poison_form": poison_form_by_scenario.get(sid),
                        "marker_type": MARKER_TYPE_BY_SCENARIO.get(sid),
                        "model": m["model"], "top_k": m["top_k"],
                        "derivation_transform": m["derivation_transform"],
                        "depth": depth, "policy": policy, "threshold": None,
                        "missed_contaminated_n": len(bt - bf),
                        **result,
                    })
                for threshold in THRESHOLDS:
                    result = blast_radius_metrics(graph, policy="thresholded", max_depth=depth, threshold=threshold)
                    bf = b_flagged(graph, policy="thresholded", max_depth=depth, threshold=threshold)
                    br_rows.append({
                        "trace_id": trace_id, "scenario_id": sid,
                        "poison_form": poison_form_by_scenario.get(sid),
                        "marker_type": MARKER_TYPE_BY_SCENARIO.get(sid),
                        "model": m["model"], "top_k": m["top_k"],
                        "derivation_transform": m["derivation_transform"],
                        "depth": depth, "policy": f"thresholded_{threshold}", "threshold": threshold,
                        "missed_contaminated_n": len(bt - bf),
                        **result,
                    })

            # H3: marker survival / laundering, every CARRIES memory in this trace.
            for nid, node in graph.nodes.items():
                if node["depth"] < 1 or node["content_label"] != "CARRIES":
                    continue
                text = content.get(nid, "") or ""
                marker_survived = any(mk in text for mk in markers) if markers else None
                h3_rows.append({
                    "trace_id": trace_id, "memory_id": nid, "scenario_id": sid,
                    "poison_form": poison_form_by_scenario.get(sid),
                    "marker_type": MARKER_TYPE_BY_SCENARIO.get(sid),
                    "model": m["model"], "derivation_transform": m["derivation_transform"],
                    "depth": node["depth"], "branch": node["branch"],
                    "marker_survived": marker_survived,
                    "laundered": (marker_survived is False),
                    "structural_lineage_reachable": nid in structural_reachable_d5,
                })

            # Clean-sibling (child_2) semantic leakage: every child_2 memory, any depth.
            for nid, node in graph.nodes.items():
                if node["branch"] != "child_2":
                    continue
                child2_rows.append({
                    "trace_id": trace_id, "memory_id": nid, "scenario_id": sid,
                    "poison_form": poison_form_by_scenario.get(sid),
                    "marker_type": MARKER_TYPE_BY_SCENARIO.get(sid),
                    "model": m["model"], "depth": node["depth"],
                    "content_label": node["content_label"],
                })
        print(f"  processed {min(i + BATCH, len(all_trace_ids))}/{len(all_trace_ids)} RD traces")

    conn.close()

    br_df = pd.DataFrame(br_rows)
    br_df.to_csv(OUT_DIR / "rd_blast_radius_raw.csv", index=False)
    h3_df = pd.DataFrame(h3_rows)
    h3_df.to_csv(OUT_DIR / "rd_h3_marker_survival_raw.csv", index=False)
    child2_df = pd.DataFrame(child2_rows)
    child2_df.to_csv(OUT_DIR / "rd_child2_leakage_raw.csv", index=False)
    print(f"\nRaw tables written: rd_blast_radius_raw.csv ({len(br_df)} rows), "
          f"rd_h3_marker_survival_raw.csv ({len(h3_df)} rows), "
          f"rd_child2_leakage_raw.csv ({len(child2_df)} rows)")

    METRICS = ["P_BR", "R_BR", "inflation_ratio", "missed_contaminated_n", "b_flagged_n"]
    valid = br_df.dropna(subset=["P_BR", "R_BR", "inflation_ratio"])

    def scenario_level(df: pd.DataFrame, extra_group=()) -> pd.DataFrame:
        group = list(extra_group) + ["policy", "depth", "scenario_id"]
        return df.groupby(group)[METRICS].mean().reset_index()

    # ---- Primary pooled summary (bootstrap CI, stratified by poison_form, n=20) ----
    sl = scenario_level(valid)
    sl["poison_form"] = sl["scenario_id"].map(poison_form_by_scenario)
    rng = np.random.default_rng(RNG_SEED)
    ci_rows = []
    for (policy, depth), g in sl.groupby(["policy", "depth"]):
        g = g.sort_values("scenario_id")
        strata = g["poison_form"].to_numpy()
        for metric in METRICS:
            vals = g[metric].to_numpy()
            mean, lo, hi = bootstrap_ci(vals, strata, N_BOOT, rng)
            ci_rows.append({"policy": policy, "depth": depth, "metric": metric,
                             "n_scenarios": len(vals), "mean": mean, "ci95_lo": lo, "ci95_hi": hi})
    summary_df = pd.DataFrame(ci_rows)
    summary_df.to_csv(OUT_DIR / "rd_summary_metrics.csv", index=False)
    print(f"\nPrimary summary (bootstrap CI, n=20 scenarios, stratified by poison_form): "
          f"{OUT_DIR / 'rd_summary_metrics.csv'}")

    # ---- By model ----
    sl_model = scenario_level(valid, extra_group=["model"])
    by_model = sl_model.groupby(["model", "policy", "depth"])[METRICS].agg(["mean", "std", "count"]).reset_index()
    by_model.to_csv(OUT_DIR / "rd_by_model.csv", index=False)

    # ---- By poison_form ----
    valid_pf = valid.copy()
    valid_pf["poison_form"] = valid_pf["scenario_id"].map(poison_form_by_scenario)
    sl_pf = scenario_level(valid_pf, extra_group=["poison_form"])
    by_pf = sl_pf.groupby(["poison_form", "policy", "depth"])[METRICS].agg(["mean", "std", "count"]).reset_index()
    by_pf.to_csv(OUT_DIR / "rd_by_poison_form.csv", index=False)

    # ---- By marker_type ----
    valid_mk = valid.copy()
    valid_mk["marker_type"] = valid_mk["scenario_id"].map(MARKER_TYPE_BY_SCENARIO)
    sl_mk = scenario_level(valid_mk, extra_group=["marker_type"])
    by_mk = sl_mk.groupby(["marker_type", "policy", "depth"])[METRICS].agg(["mean", "std", "count"]).reset_index()
    by_mk.to_csv(OUT_DIR / "rd_by_marker_type.csv", index=False)

    # ---- By transform x top_k (optional, pooled at depth=5) ----
    at5 = valid[valid["depth"] == 5]
    by_transform_topk = (
        at5.groupby(["derivation_transform", "top_k", "policy"])[METRICS].mean().reset_index()
    )
    by_transform_topk.to_csv(OUT_DIR / "rd_by_transform_topk.csv", index=False)

    print(f"Breakdown tables written: rd_by_model.csv, rd_by_poison_form.csv, "
          f"rd_by_marker_type.csv, rd_by_transform_topk.csv")

    # ---- H3 laundering summary ----
    scored = h3_df[h3_df["marker_survived"].notna()]
    h3_summary = (
        scored.groupby(["model", "derivation_transform"])
        .agg(n_carries=("laundered", "size"), n_laundered=("laundered", "sum"),
             laundering_rate=("laundered", "mean"),
             structural_lineage_recall=("structural_lineage_reachable", "mean"))
        .reset_index()
    )
    h3_summary.to_csv(OUT_DIR / "rd_h3_laundering.csv", index=False)
    overall_laundering = scored["laundered"].mean() if len(scored) else float("nan")
    print(f"\nH3 laundering summary: {OUT_DIR / 'rd_h3_laundering.csv'}")
    print(f"  Overall RD laundering rate (pooled over {len(scored)} CARRIES memories, "
          f"NOT the primary estimand -- see scenario-level CI below): {overall_laundering:.4%} "
          f"({int(scored['laundered'].sum())}/{len(scored)})")

    # ---- H3 laundering rate, scenario-level bootstrap CI (n=20, primary estimand) ----
    # Per docs/preregistration.md SS5's marginalization rule: average within each
    # scenario first (here, across all its CARRIES memories, since this slice has 1
    # seed), then treat each of the 20 scenarios as one equally-weighted resampling
    # unit -- same discipline as the child_2 leakage CI directly below. A scenario
    # with zero CARRIES memories has an undefined per-scenario laundering rate and is
    # excluded from this specific CI (still present in the pooled/by-breakdown tables
    # above), noted in n_scenarios.
    h3_scenario_rows = []
    for sid in sorted(poison_form_by_scenario):
        g = scored[scored["scenario_id"] == sid]
        h3_scenario_rows.append({
            "scenario_id": sid,
            "poison_form": poison_form_by_scenario.get(sid),
            "n_carries": len(g),
            "laundering_rate": g["laundered"].mean() if len(g) else None,
        })
    h3_scenario_df = pd.DataFrame(h3_scenario_rows)
    h3_scenario_df.to_csv(OUT_DIR / "rd_h3_laundering_by_scenario.csv", index=False)
    h3_scored_scenarios = h3_scenario_df.dropna(subset=["laundering_rate"])
    h3_vals = h3_scored_scenarios["laundering_rate"].to_numpy()
    h3_strata = h3_scored_scenarios["poison_form"].to_numpy()
    h3_mean, h3_lo, h3_hi = bootstrap_ci(h3_vals, h3_strata, N_BOOT, np.random.default_rng(RNG_SEED))
    print(f"\nH3 laundering rate, scenario-level bootstrap CI "
          f"(n={len(h3_vals)} scenarios with >=1 CARRIES memory, stratified by poison_form):")
    print(f"  mean={h3_mean:.4f} [{h3_lo:.4f}, {h3_hi:.4f}]")
    print(f"  Per-scenario table: {OUT_DIR / 'rd_h3_laundering_by_scenario.csv'}")

    # ---- Clean-sibling (child_2) semantic leakage rate ----
    child2_summary_rows = []
    for sid, g in child2_df.groupby("scenario_id"):
        n = len(g)
        n_carries = (g["content_label"] == "CARRIES").sum()
        n_ref = (g["content_label"] == "REFERENCES").sum()
        child2_summary_rows.append({
            "scenario_id": sid,
            "poison_form": poison_form_by_scenario.get(sid),
            "marker_type": MARKER_TYPE_BY_SCENARIO.get(sid),
            "n_child2": n,
            "carries_rate": n_carries / n if n else None,
            "carries_or_references_rate": (n_carries + n_ref) / n if n else None,
        })
    child2_summary = pd.DataFrame(child2_summary_rows).sort_values("scenario_id")
    child2_summary.to_csv(OUT_DIR / "rd_child2_leakage_summary.csv", index=False)
    strict_vals = child2_summary["carries_rate"].to_numpy()
    broad_vals = child2_summary["carries_or_references_rate"].to_numpy()
    strata = child2_summary["poison_form"].to_numpy()
    strict_mean, strict_lo, strict_hi = bootstrap_ci(strict_vals, strata, N_BOOT, np.random.default_rng(RNG_SEED))
    broad_mean, broad_lo, broad_hi = bootstrap_ci(broad_vals, strata, N_BOOT, np.random.default_rng(RNG_SEED))
    print(f"\nClean-sibling (child_2) semantic leakage, n=20 scenarios:")
    print(f"  Strict (CARRIES only):        mean={strict_mean:.4f} [{strict_lo:.4f}, {strict_hi:.4f}]")
    print(f"  Broad (CARRIES+REFERENCES):   mean={broad_mean:.4f} [{broad_lo:.4f}, {broad_hi:.4f}]")
    print(f"  Per-scenario table: {OUT_DIR / 'rd_child2_leakage_summary.csv'}")

    print("\n=== Headline (depth=5, all policies, pooled mean [95% CI], n=20 scenarios) ===")
    show = summary_df[(summary_df["depth"] == 5) & (summary_df["metric"].isin(["P_BR", "R_BR", "inflation_ratio"]))]
    print(show.sort_values(["policy", "metric"]).to_string(index=False))


if __name__ == "__main__":
    main()
