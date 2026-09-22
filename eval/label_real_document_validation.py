"""Labels derived memories from the real-document validation slice
(configs/scenarios/real_documents/RD01..RD20.yaml) using the exact same
FROZEN labeler pipeline (src/memoryir/labeler.py, unchanged since the
kappa=0.8699/0.8838 validation) that eval/label_full_corpus.py uses for
the synthetic corpus -- LLMJudge, NLIVerifier, and label_one are all
imported unmodified, not reimplemented.

Separate entry point from eval/label_full_corpus.py for exactly one
reason: that script's semantic_target lookup is built from
load_all_scenarios(SCENARIOS_DIR), which only loads the 30 synthetic
scenarios (configs/scenarios/*.yaml + pilot/), not
configs/scenarios/real_documents/. Running label_full_corpus.py
unmodified against RD memories fails with KeyError on every row (caught
by the 2026-09-22 smoke test, not fixed by touching that script or
load_all_scenarios() -- this new script exists instead, so the frozen
labeling path stays untouched exactly as agreed).

The WHERE clause below is scoped to scenario_id LIKE 'RD%' specifically
so this script can never accidentally claim and attempt to label a
synthetic-corpus memory that happens to have content_label IS NULL for
some other reason.

Usage:
    python eval/label_real_document_validation.py --dry-run
    python eval/label_real_document_validation.py --launch --workers 3
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
from memoryir.scenarios import load_scenario

RD_SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios" / "real_documents"
RUN_META_DIR = REPO_ROOT / "results" / "real_document_validation"


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
                "the kappa=0.8699/0.8838 validation, applied to the real-document "
                "validation slice via its own scenario lookup (see module docstring).",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **extra,
    }
    (RUN_META_DIR / f"labeling_run_meta_{label}_{int(time.time())}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def _fetch_pending(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, scenario_id, content FROM memories "
        "WHERE branch IN ('child_1','child_2','child_3') AND content_label IS NULL "
        "AND scenario_id LIKE 'RD%' "
        "ORDER BY id"
    ).fetchall()
    return [{"id": r[0], "scenario_id": r[1], "content": r[2]} for r in rows]


_thread_state = threading.local()


def _get_thread_resources():
    if not hasattr(_thread_state, "judge"):
        _thread_state.conn = db.connect(embed_dim=384)
        _thread_state.judge = LLMJudge(
            log_dir=REPO_ROOT / "results" / "real_document_validation_labeling_llm_log" / f"thread_{threading.get_ident()}"
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


def load_rd_target_lookup() -> dict:
    paths = sorted(RD_SCENARIOS_DIR.glob("*.yaml"))
    specs = [load_scenario(p) for p in paths]
    return {s["scenario_id"]: s["semantic_target"]["definition"] for s in specs}


def do_dry_run() -> list[dict]:
    conn = db.connect(embed_dim=384)
    pending = _fetch_pending(conn)
    conn.close()
    target_by_scenario = load_rd_target_lookup()
    print(f"Pending RD memories (content_label IS NULL, scenario_id LIKE 'RD%'): {len(pending)}")
    print(f"RD scenarios loaded for semantic_target lookup: {len(target_by_scenario)}")
    unknown = {r["scenario_id"] for r in pending} - set(target_by_scenario)
    if unknown:
        raise SystemExit(f"FATAL: pending memories reference unknown RD scenario_id(s): {unknown}")
    return pending


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--launch", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    pending = do_dry_run()
    if args.dry_run:
        return

    target_by_scenario = load_rd_target_lookup()
    label = "full"
    print(f"\nLAUNCHING RD LABELING: {len(pending)} memories, {args.workers} workers...")

    RUN_META_DIR.mkdir(parents=True, exist_ok=True)
    error_log_path = RUN_META_DIR / f"labeling_errors_{label}_{int(time.time())}.log"
    _record_run_meta(label, {"n_rows": len(pending), "workers": args.workers})

    t_start = time.time()
    done = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_label_row, r, target_by_scenario, error_log_path): r for r in pending}
        for i, fut in enumerate(as_completed(futures), start=1):
            _, ok = fut.result()
            done += ok
            failed += not ok
            if i % 50 == 0 or i == len(pending):
                elapsed = time.time() - t_start
                print(f"  [{i}/{len(pending)}] done={done} failed={failed} elapsed={elapsed:.0f}s")

    print(f"\nDone. {done} labeled, {failed} failed (see {error_log_path}; "
          f"failed rows stay content_label=NULL, safe to re-run this script to retry).")


if __name__ == "__main__":
    main()
