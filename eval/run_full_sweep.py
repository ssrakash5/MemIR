"""Full-sweep generation runner -- walks the entire frozen
generation_factors grid (configs/experiment_grid.yaml), NOT the scoped v1
harness eval/run.py still uses for labeling-validation smoke tests. That
script is left untouched; this is a separate entry point.

5,760 traces = 24 scenarios x 4 top_k x 3 write_fanout x 4
derivation_transform x 5 seeds. See docs/preregistration.md SS4 for the
frozen sample-size design this implements (24 scenarios is the real
inferential unit; the 5 seeds are within-scenario noise reduction, not
extra replicates -- see the three frozen seed rules there).

child_3 (only present at write_fanout=3) has no scenario-authored true
parent -- per an explicit AskUserQuestion decision (2026-08-12, this
session): treated as a distractor-only sibling at every depth, mirroring
the pattern already used for child_2 at continuation depths. Implemented
in src/memoryir/harness.py.

Checkpointing: every enumerated trace key is a row in Postgres'
sweep_runs table (src/memoryir/db.py). A trace is only ever marked 'done'
after generate_trace() returns without raising. A transient failure
retries the SAME trace_id/seed (never a new seed) up to --max-attempts
times; attempts are counted on the row itself, separately from the seed
axis. Any row still 'running' at process start (a crash mid-generation)
is reset to 'pending' and its partial memory/memory_influence rows are
deleted before regeneration -- retries are idempotent, never duplicate.

Usage:
    python eval/run_full_sweep.py --dry-run
    python eval/run_full_sweep.py --smoke-test 3
    python eval/run_full_sweep.py --launch --workers 3
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
from memoryir.scenarios import load_all_scenarios
from memoryir.sweep_grid import enumerate_cells, load_generation_factors, sanity_check

GRID_PATH = REPO_ROOT / "configs" / "experiment_grid.yaml"
SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios"
RUN_META_DIR = REPO_ROOT / "results" / "full_sweep"


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
        "config_snapshot": GRID_PATH.read_text(encoding="utf-8"),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **extra,
    }
    path = RUN_META_DIR / f"run_meta_{label}_{int(time.time())}.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Run metadata recorded: {path}")


def do_dry_run() -> list[dict]:
    factors = load_generation_factors(GRID_PATH)
    specs = load_all_scenarios(SCENARIOS_DIR)
    cells = enumerate_cells(grid_path=GRID_PATH, scenarios_dir=SCENARIOS_DIR)
    sanity_check(cells, factors, n_scenarios=len(specs))
    print("DRY-RUN SANITY CHECK: PASSED")
    print(f"  {len(cells)} unique trace keys enumerated")
    print(f"  scenarios: {len(specs)}  top_k: {factors['top_k']}  "
          f"write_fanout: {factors['write_fanout']}  "
          f"derivation_transform: {factors['derivation_transform']}  "
          f"seeds: {factors['seeds']}")
    return cells


_thread_state = threading.local()


def _get_thread_resources(model: str):
    """Lazily creates ONE embedder + DB connection per worker thread
    (keyed on the real OS thread id), reused across every cell that
    thread processes. LLM clients are cached per (thread, model) in a
    dict, since one thread may process cells for different models across
    its lifetime (e.g. gpt-4o and llama-3.3-70b interleaved)."""
    if not hasattr(_thread_state, "embedder"):
        _thread_state.embedder = Embedder()
        _thread_state.conn = db.connect(embed_dim=_thread_state.embedder.dim)
        _thread_state.llm_by_model = {}
    if model not in _thread_state.llm_by_model:
        _thread_state.llm_by_model[model] = make_llm_client(
            model,
            log_dir=REPO_ROOT / "results" / "full_sweep_llm_log" / model / f"thread_{threading.get_ident()}",
        )
    return _thread_state.embedder, _thread_state.conn, _thread_state.llm_by_model[model]


def _worker(cell: dict, spec_by_id: dict, max_attempts: int) -> tuple[str, bool, str | None]:
    trace_id = cell["trace_id"]
    embedder, conn, llm = _get_thread_resources(cell["model"])
    try:
        if not db.claim_trace(conn, trace_id, max_attempts=max_attempts):
            return trace_id, False, "not claimed (already done/claimed/exhausted)"
        db.delete_trace_rows(conn, trace_id)  # idempotent retry
        spec = spec_by_id[cell["scenario_id"]]
        config = TraceConfig(
            top_k=cell["top_k"],
            write_fanout=cell["write_fanout"],
            derivation_transform=cell["derivation_transform"],
            seed=cell["seed"],
            max_depth=5,
            model=cell["model"],
        )
        generate_trace(spec, config, conn, llm, embedder, trace_id=trace_id)
        db.mark_done(conn, trace_id)
        return trace_id, True, None
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        db.mark_failed(conn, trace_id, err)
        return trace_id, False, str(e)


def run_cells(cells: list[dict], *, workers: int, max_attempts: int, label: str) -> None:
    embedder = Embedder()
    conn = db.connect(embed_dim=embedder.dim)
    specs = load_all_scenarios(SCENARIOS_DIR)
    spec_by_id = {s["scenario_id"]: s for s in specs}

    n_reset = db.reset_stuck_running(conn)
    if n_reset:
        print(f"Reset {n_reset} stuck 'running' rows from a prior crashed process.")
    db.seed_sweep_runs(conn, cells)

    counts = db.sweep_status_counts(conn)
    print(f"sweep_runs status: {counts}")
    todo = [c for c in cells]  # _worker re-checks claimability itself
    conn.close()

    _record_run_meta(label, {"n_cells": len(cells), "workers": workers, "max_attempts": max_attempts})

    t_start = time.time()
    done = failed = skipped = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_worker, c, spec_by_id, max_attempts): c
            for c in todo
        }
        for i, fut in enumerate(as_completed(futures), start=1):
            trace_id, ok, err = fut.result()
            if ok:
                done += 1
            elif err and "not claimed" in err:
                skipped += 1
            else:
                failed += 1
                print(f"  [{i}/{len(todo)}] FAILED {trace_id}: {err}")
            if i % 25 == 0 or i == len(todo):
                elapsed = time.time() - t_start
                print(f"  [{i}/{len(todo)}] done={done} failed={failed} skipped={skipped} "
                      f"elapsed={elapsed:.0f}s")

    conn = db.connect(embed_dim=embedder.dim)
    final_counts = db.sweep_status_counts(conn)
    conn.close()
    print(f"\nFinal sweep_runs status: {final_counts}")
    if final_counts.get("error_exhausted"):
        print(f"WARNING: {final_counts['error_exhausted']} traces exhausted "
              f"{max_attempts} attempts and were left for manual review -- "
              f"see sweep_runs.last_error. This needs a dated deviation-log "
              f"entry once diagnosed, not a silent retry-forever loop.")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Enumerate + sanity-check only, no DB/API calls.")
    mode.add_argument("--smoke-test", type=int, metavar="N", help="Run N real traces end-to-end (checkpointed), then stop.")
    mode.add_argument("--launch", action="store_true", help="Run the full sweep (resumable).")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=5)
    args = parser.parse_args()

    if args.dry_run:
        do_dry_run()
        return

    cells = do_dry_run()  # always sanity-check before touching the DB/API

    if args.smoke_test:
        subset = cells[: args.smoke_test]
        print(f"\nSMOKE TEST: running {len(subset)} real traces end-to-end...")
        run_cells(subset, workers=min(args.workers, len(subset)), max_attempts=args.max_attempts, label="smoke")
        return

    print(f"\nLAUNCHING FULL SWEEP: {len(cells)} traces, {args.workers} workers, "
          f"max_attempts={args.max_attempts}...")
    run_cells(cells, workers=args.workers, max_attempts=args.max_attempts, label="full")


if __name__ == "__main__":
    main()
