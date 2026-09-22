"""Generation runner for the real-document validation slice
(configs/scenarios/real_documents/RD01..RD20.yaml) -- separate entry
point from eval/run_full_sweep.py, deliberately NOT built on
load_all_scenarios() or enumerate_cells()/configs/experiment_grid.yaml,
so the frozen 30-scenario synthetic corpus is untouched by construction,
not just by convention.

Loads each RDxx spec directly via memoryir.scenarios.load_scenario() from
configs/scenarios/real_documents/*.yaml. Everything else -- the harness
(generate_trace), the Postgres checkpoint tables (sweep_runs, memories,
memory_influence), and the labeling pipeline (eval/label_full_corpus.py,
run unmodified afterward) -- is the exact same frozen machinery the
synthetic corpus uses. Per real_documents/VALIDATION_CHECKLIST.md's
smoke-test plan (2026-09-22): content_label, structural edges, and
marker-survival metrics must be written identically to synthetic runs,
not through a parallel implementation.

Reduced grid (agreed with the user, not the full experiment_grid.yaml):
  --smoke: RD01-RD04 (one of each poison_form/marker_type pair) x
           gpt-4o-mini x top_k=5 x write_fanout=2 x summarize x seed=0 x
           max_depth=3. 4 traces total, cheap plumbing check only.
  --launch: all 20 RD scenarios x 3 models x top_k in {5, 10} x
            write_fanout=2 x transform in {summarize, paraphrase} x
            seed=0 x max_depth=5. 20*3*2*2 = 240 traces.

Usage:
    python eval/run_real_document_validation.py --dry-run
    python eval/run_real_document_validation.py --smoke
    python eval/run_real_document_validation.py --launch --workers 3
"""
import argparse
import json
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from memoryir import db
from memoryir.embeddings import Embedder
from memoryir.harness import TraceConfig, generate_trace
from memoryir.llm import make_llm_client
from memoryir.scenarios import load_scenario
from memoryir.sweep_grid import trace_key

RD_SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios" / "real_documents"
RUN_META_DIR = REPO_ROOT / "results" / "real_document_validation"

SMOKE_SCENARIO_IDS = [
    "RD01_nist_ai_rmf_govern",       # authoritative_framing, email_domain
    "RD02_aws_ecs_anywhere",         # multi_hop_setup, invented_id
    "RD03_nist_genai_infosec",       # direct_instruction, numeric_time
    "RD04_nist_csf_tiers",           # embedded_fact, natural_language
]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "UNKNOWN"


def _record_run_meta(label: str, extra: dict) -> None:
    RUN_META_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "label": label,
        "git_commit": _git_commit(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **extra,
    }
    path = RUN_META_DIR / f"run_meta_{label}_{int(time.time())}.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Run metadata recorded: {path}")
    if meta["git_commit"] == "UNKNOWN" or _is_dirty():
        print(
            "  NOTE: working tree is dirty or commit lookup failed -- this run "
            "is NOT reproducible from a clean commit hash. Fine for the smoke "
            "test; the full --launch run should happen after the construction "
            "commit per the agreed sequence."
        )


def _is_dirty() -> bool:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True)
        return bool(out.strip())
    except Exception:
        return True


def load_rd_specs(scenario_ids: list[str] | None = None) -> list[dict]:
    paths = sorted(RD_SCENARIOS_DIR.glob("*.yaml"))
    specs = [load_scenario(p) for p in paths]
    if scenario_ids is not None:
        wanted = set(scenario_ids)
        specs = [s for s in specs if s["scenario_id"] in wanted]
        found = {s["scenario_id"] for s in specs}
        missing = wanted - found
        if missing:
            raise SystemExit(f"FATAL: requested scenario_id(s) not found: {missing}")
    return specs


def enumerate_rd_cells(specs: list[dict], *, models: list[str], top_ks: list[int],
                        write_fanouts: list[int], transforms: list[str],
                        seeds: list[int], max_depth: int) -> list[dict]:
    cells = []
    for spec in specs:
        for model in models:
            for top_k in top_ks:
                for write_fanout in write_fanouts:
                    for transform in transforms:
                        for seed in seeds:
                            cells.append({
                                "scenario_id": spec["scenario_id"],
                                "model": model,
                                "top_k": top_k,
                                "write_fanout": write_fanout,
                                "derivation_transform": transform,
                                "seed": seed,
                                "max_depth": max_depth,
                                "trace_id": trace_key(
                                    scenario_id=spec["scenario_id"],
                                    model=model,
                                    top_k=top_k,
                                    write_fanout=write_fanout,
                                    derivation_transform=transform,
                                    seed=seed,
                                ),
                            })
    return cells


def do_dry_run(cells: list[dict], specs: list[dict]) -> None:
    ids = [c["trace_id"] for c in cells]
    assert len(ids) == len(set(ids)), f"duplicate trace_ids: {len(ids) - len(set(ids))}"
    for c in cells:
        assert c["scenario_id"].startswith("RD"), (
            f"non-RD scenario_id {c['scenario_id']} leaked into this runner -- "
            f"this must never touch the synthetic 30-scenario corpus"
        )
    print("DRY-RUN SANITY CHECK: PASSED")
    print(f"  {len(cells)} unique trace keys enumerated across {len(specs)} RD scenarios")
    print(f"  models: {sorted({c['model'] for c in cells})}")
    print(f"  top_k: {sorted({c['top_k'] for c in cells})}")
    print(f"  write_fanout: {sorted({c['write_fanout'] for c in cells})}")
    print(f"  transforms: {sorted({c['derivation_transform'] for c in cells})}")
    print(f"  seeds: {sorted({c['seed'] for c in cells})}")
    print(f"  max_depth: {sorted({c['max_depth'] for c in cells})}")


_thread_state = threading.local()


def _get_thread_resources(model: str):
    if not hasattr(_thread_state, "embedder"):
        _thread_state.embedder = Embedder()
        _thread_state.conn = db.connect(embed_dim=_thread_state.embedder.dim)
        _thread_state.llm_by_model = {}
    if model not in _thread_state.llm_by_model:
        _thread_state.llm_by_model[model] = make_llm_client(
            model,
            log_dir=REPO_ROOT / "results" / "real_document_validation_llm_log" / model / f"thread_{threading.get_ident()}",
        )
    return _thread_state.embedder, _thread_state.conn, _thread_state.llm_by_model[model]


def _worker(cell: dict, spec_by_id: dict, max_attempts: int) -> tuple[str, bool, str | None]:
    trace_id = cell["trace_id"]
    embedder, conn, llm = _get_thread_resources(cell["model"])
    try:
        if not db.claim_trace(conn, trace_id, max_attempts=max_attempts):
            return trace_id, False, "not claimed (already done/claimed/exhausted)"
        db.delete_trace_rows(conn, trace_id)
        spec = spec_by_id[cell["scenario_id"]]
        config = TraceConfig(
            top_k=cell["top_k"],
            write_fanout=cell["write_fanout"],
            derivation_transform=cell["derivation_transform"],
            seed=cell["seed"],
            max_depth=cell["max_depth"],
            model=cell["model"],
        )
        generate_trace(spec, config, conn, llm, embedder, trace_id=trace_id)
        db.mark_done(conn, trace_id)
        return trace_id, True, None
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        db.mark_failed(conn, trace_id, err)
        return trace_id, False, str(e)


def run_cells(cells: list[dict], specs: list[dict], *, workers: int, max_attempts: int, label: str) -> None:
    embedder = Embedder()
    conn = db.connect(embed_dim=embedder.dim)
    spec_by_id = {s["scenario_id"]: s for s in specs}

    n_reset = db.reset_stuck_running(conn)
    if n_reset:
        print(f"Reset {n_reset} stuck 'running' rows from a prior crashed process.")
    db.seed_sweep_runs(conn, cells)

    counts = db.sweep_status_counts(conn)
    print(f"sweep_runs status (RD trace_ids among all): {counts}")
    conn.close()

    _record_run_meta(label, {"n_cells": len(cells), "workers": workers, "max_attempts": max_attempts,
                              "scenario_ids": sorted({c["scenario_id"] for c in cells})})

    t_start = time.time()
    done = failed = skipped = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, c, spec_by_id, max_attempts): c for c in cells}
        for i, fut in enumerate(as_completed(futures), start=1):
            trace_id, ok, err = fut.result()
            if ok:
                done += 1
            elif err and "not claimed" in err:
                skipped += 1
            else:
                failed += 1
                print(f"  [{i}/{len(cells)}] FAILED {trace_id}: {err}")
            if i % 10 == 0 or i == len(cells):
                elapsed = time.time() - t_start
                print(f"  [{i}/{len(cells)}] done={done} failed={failed} skipped={skipped} elapsed={elapsed:.0f}s")

    conn = db.connect(embed_dim=embedder.dim)
    rd_trace_ids = [c["trace_id"] for c in cells]
    rows = conn.execute(
        "SELECT status, count(*) FROM sweep_runs WHERE trace_id = ANY(%s) GROUP BY status",
        (rd_trace_ids,),
    ).fetchall()
    conn.close()
    print(f"\nFinal status for this run's {len(cells)} RD trace_ids: {dict(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="RD01-RD04, 1 model, 1 cell each -- 4 traces.")
    mode.add_argument("--launch", action="store_true", help="All 20 RD scenarios, full reduced grid -- 240 traces.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Modifier: enumerate + sanity-check only, no DB/API calls. Combine with --smoke or --launch.")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=5)
    args = parser.parse_args()

    if args.smoke:
        specs = load_rd_specs(SMOKE_SCENARIO_IDS)
        cells = enumerate_rd_cells(
            specs,
            models=["gpt-4o-mini"],
            top_ks=[5],
            write_fanouts=[2],
            transforms=["summarize"],
            seeds=[0],
            max_depth=3,
        )
    else:
        specs = load_rd_specs()
        assert len(specs) == 20, f"expected all 20 RD scenarios, found {len(specs)}"
        cells = enumerate_rd_cells(
            specs,
            models=["gpt-4o-mini", "gpt-4o", "llama-3.3-70b"],
            top_ks=[5, 10],
            write_fanouts=[2],
            transforms=["summarize", "paraphrase"],
            seeds=[0],
            max_depth=5,
        )
        if args.launch:
            assert len(cells) == 240, f"expected 240 cells for the full RD launch, got {len(cells)}"

    do_dry_run(cells, specs)

    if args.dry_run:
        return

    label = "smoke" if args.smoke else "full"
    print(f"\nLAUNCHING REAL-DOCUMENT VALIDATION ({label.upper()}): {len(cells)} traces, "
          f"{args.workers} workers, max_attempts={args.max_attempts}...")
    run_cells(cells, specs, workers=args.workers, max_attempts=args.max_attempts, label=label)


if __name__ == "__main__":
    main()
