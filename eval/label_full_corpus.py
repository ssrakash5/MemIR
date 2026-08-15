"""Labels every derived memory in the full 5,760-trace sweep using the
FROZEN labeler pipeline (src/memoryir/labeler.py) -- unchanged since the
kappa validation that passed at kappa=0.8699/0.8838. This script does not
touch the rubric, the combination rule, or the compositional-target
instruction; it only runs that already-validated pipeline at corpus
scale instead of on the 120-sample calibration set.

Checkpointing: memories.content_label IS NULL is the resume signal
itself -- no separate tracking table needed, since each label is a
single atomic UPDATE (unlike trace generation's multi-row inserts, there
is no partial-write state to clean up on a crash/kill). Re-running this
script only ever processes rows still NULL.

Usage:
    python eval/label_full_corpus.py --dry-run
    python eval/label_full_corpus.py --launch --workers 3
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
from memoryir.labeler import LLMJudge, NLIVerifier, label_one
from memoryir.scenarios import load_all_scenarios

SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios"
RUN_META_DIR = REPO_ROOT / "results" / "full_labeling"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def _record_run_meta(label: str, extra: dict) -> None:
    RUN_META_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "label": label,
        "git_commit": _git_commit(),
        "note": "Frozen labeler pipeline (src/memoryir/labeler.py), unchanged since "
                "the kappa=0.8699/0.8838 validation. This run applies it at full "
                "corpus scale only.",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **extra,
    }
    (RUN_META_DIR / f"run_meta_{label}_{int(time.time())}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def _fetch_pending(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, scenario_id, content FROM memories "
        "WHERE branch IN ('child_1','child_2','child_3') AND content_label IS NULL "
        "ORDER BY id"
    ).fetchall()
    return [{"id": r[0], "scenario_id": r[1], "content": r[2]} for r in rows]


_thread_state = threading.local()


def _get_thread_resources():
    if not hasattr(_thread_state, "judge"):
        _thread_state.conn = db.connect(embed_dim=384)
        _thread_state.judge = LLMJudge(
            log_dir=REPO_ROOT / "results" / "full_labeling_llm_log" / f"thread_{threading.get_ident()}"
        )
        _thread_state.nli = NLIVerifier()
    return _thread_state.conn, _thread_state.judge, _thread_state.nli


def _label_row(row: dict, target_by_scenario: dict, error_log_path: Path) -> tuple[int, bool]:
    conn, judge, nli = _get_thread_resources()
    try:
        result = label_one(
            semantic_target=target_by_scenario[row["scenario_id"]],
            candidate=row["content"],
            judge=judge,
            nli=nli,
        )
        conn.execute(
            "UPDATE memories SET content_label=%s WHERE id=%s", (result.final_label, row["id"])
        )
        return row["id"], True
    except Exception as e:
        err = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} memory_id={row['id']} {type(e).__name__}: {e}\n{traceback.format_exc()}\n"
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(err)
        return row["id"], False


def do_dry_run() -> list[dict]:
    conn = db.connect(embed_dim=384)
    pending = _fetch_pending(conn)
    conn.close()
    specs = load_all_scenarios(SCENARIOS_DIR)
    print(f"Pending (content_label IS NULL): {len(pending)}")
    print(f"Scenarios loaded for semantic_target lookup: {len(specs)}")
    return pending


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--smoke-test", type=int, metavar="N")
    mode.add_argument("--launch", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    pending = do_dry_run()
    if args.dry_run:
        return

    specs = load_all_scenarios(SCENARIOS_DIR)
    target_by_scenario = {s["scenario_id"]: s["semantic_target"]["definition"] for s in specs}

    todo = pending[: args.smoke_test] if args.smoke_test else pending
    label = "smoke" if args.smoke_test else "full"
    print(f"\n{'SMOKE TEST' if args.smoke_test else 'LAUNCHING FULL LABELING'}: "
          f"{len(todo)} memories, {args.workers} workers...")

    RUN_META_DIR.mkdir(parents=True, exist_ok=True)
    error_log_path = RUN_META_DIR / f"errors_{label}_{int(time.time())}.log"
    _record_run_meta(label, {"n_rows": len(todo), "workers": args.workers})

    t_start = time.time()
    done = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_label_row, r, target_by_scenario, error_log_path): r for r in todo}
        for i, fut in enumerate(as_completed(futures), start=1):
            _, ok = fut.result()
            done += ok
            failed += not ok
            if i % 500 == 0 or i == len(todo):
                elapsed = time.time() - t_start
                print(f"  [{i}/{len(todo)}] done={done} failed={failed} elapsed={elapsed:.0f}s")

    print(f"\nDone. {done} labeled, {failed} failed (see {error_log_path}; "
          f"failed rows stay content_label=NULL, safe to re-run this script to retry).")


if __name__ == "__main__":
    main()
