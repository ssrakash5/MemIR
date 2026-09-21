"""One-off, reviewable invalidation of Postgres rows for the 3
clean_control scenarios whose benign source facts were revised in the
2026-09-21 human review (see configs/scenarios/clean_control_review.md).

WHY THIS SCRIPT EXISTS: generation is checkpointed by trace_id
(scenario_id, model, top_k, write_fanout, derivation_transform, seed) --
NOT a content hash of the scenario YAML. sweep_runs rows for
clean_control_03/05/06 are already marked 'done' from the original
2026-08-15 overnight run, and claim_trace() only ever retries
'pending'/'failed' rows. So simply re-running eval/run_full_sweep.py
after editing the YAMLs would silently SKIP these 3 scenarios, leaving
the DB -- and results/metrics/clean_control_false_positive*.csv -- built
from the pre-edit B1/B2 text. This script explicitly invalidates their
existing rows so the next sweep run regenerates them for real.

This script does NOT call any LLM/embedding API and does NOT run
generation itself -- it only inspects, and with --apply, snapshots +
deletes rows for the three target scenarios in a single transaction.

Usage:
    python eval/invalidate_clean_control_scenarios.py           # dry run: verify + report counts only
    python eval/invalidate_clean_control_scenarios.py --apply    # snapshot, then delete, in one transaction

After --apply, the documented rerun order (see
configs/scenarios/clean_control_review.md and eval/README.md) is:
    python eval/run_full_sweep.py --launch --workers 3 --max-attempts 5
    python eval/label_full_corpus.py --launch --workers 3
    python eval/compute_clean_control_metrics.py
    python eval/make_figures.py
Not run by this script -- these cost real Azure API calls.
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from memoryir import db

SCENARIOS_DIR = REPO_ROOT / "configs" / "scenarios"
METRICS_DIR = REPO_ROOT / "results" / "metrics"
SNAPSHOT_ROOT = REPO_ROOT / "results" / "clean_control_pre_regeneration_snapshot"

# Hardcoded, not CLI-supplied: the exact 3 scenarios revised in the
# 2026-09-21 review (configs/scenarios/clean_control_review.md).
# Deliberately not parameterized -- a copy-pasted future invocation of
# this script can't accidentally widen the blast radius to scenarios
# that were never touched, since there's no argument to widen.
TARGET_SCENARIOS = ("clean_control_03", "clean_control_05", "clean_control_06")


def verify_target_scenarios() -> None:
    """Fail loudly before touching the DB if the hardcoded target list
    doesn't match what's actually on disk."""
    if len(set(TARGET_SCENARIOS)) != 3:
        raise SystemExit("FATAL: TARGET_SCENARIOS must contain exactly 3 distinct scenario_ids.")
    for sid in TARGET_SCENARIOS:
        path = SCENARIOS_DIR / f"{sid}.yaml"
        if not path.exists():
            raise SystemExit(f"FATAL: expected scenario file missing: {path}")
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        if spec.get("scenario_id") != sid:
            raise SystemExit(
                f"FATAL: {path} declares scenario_id={spec.get('scenario_id')!r}, expected {sid!r}"
            )
        if spec.get("poison_form") != "clean_control":
            raise SystemExit(
                f"FATAL: {sid} has poison_form={spec.get('poison_form')!r}, expected "
                f"'clean_control' -- refusing to invalidate a non-clean_control scenario."
            )


def get_counts(conn, scenario_ids: list[str]) -> tuple[dict, list[str]]:
    counts: dict[str, int] = {}
    counts["sweep_runs"] = conn.execute(
        "SELECT count(*) FROM sweep_runs WHERE scenario_id = ANY(%s)", (scenario_ids,)
    ).fetchone()[0]
    trace_ids = [
        r[0] for r in conn.execute(
            "SELECT trace_id FROM sweep_runs WHERE scenario_id = ANY(%s)", (scenario_ids,)
        ).fetchall()
    ]
    counts["memories"] = conn.execute(
        "SELECT count(*) FROM memories WHERE scenario_id = ANY(%s)", (scenario_ids,)
    ).fetchone()[0]
    counts["memory_influence"] = (
        conn.execute(
            "SELECT count(*) FROM memory_influence WHERE trace_id = ANY(%s)", (trace_ids,)
        ).fetchone()[0]
        if trace_ids
        else 0
    )
    return counts, trace_ids


def write_snapshot(total_counts: dict, per_scenario_counts: dict) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    for name in ("clean_control_false_positive.csv", "clean_control_false_positive_raw.csv"):
        src = METRICS_DIR / name
        if src.exists():
            shutil.copy2(src, out_dir / name)

    manifest = {
        "taken_at_utc": ts,
        "reason": (
            "Pre-regeneration snapshot before invalidating and regenerating "
            "clean_control_03/05/06 rows after the 2026-09-21 human review "
            "revised their benign B1/B2 source facts "
            "(configs/scenarios/clean_control_review.md)."
        ),
        "target_scenarios": list(TARGET_SCENARIOS),
        "row_counts_about_to_be_deleted": total_counts,
        "per_scenario_row_counts": per_scenario_counts,
        "note": (
            "clean_control_false_positive*.csv copies in this directory, if "
            "present, are the STALE pre-edit baseline (generated from "
            "pre-2026-09-21 scenario text) -- kept for the paper's review "
            "trail, not for reporting."
        ),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually snapshot + delete. Without this flag, only reports counts (dry run, default).",
    )
    args = parser.parse_args()

    verify_target_scenarios()
    print(f"Target scenarios (hardcoded, verified against configs/scenarios/*.yaml): {TARGET_SCENARIOS}")

    try:
        # connect_timeout: psycopg's default connect has no timeout and can
        # hang a long time against an unreachable host rather than failing
        # fast -- give this script a bounded, clearly-diagnosable failure.
        import os

        import psycopg
        from pgvector.psycopg import register_vector

        url = os.environ.get("DATABASE_URL", db.DEFAULT_DATABASE_URL)
        conn = psycopg.connect(url, autocommit=True, connect_timeout=10)
        register_vector(conn)
        for stmt in db.SCHEMA_STATEMENTS:
            conn.execute(stmt.format(embed_dim=384))
    except Exception as e:
        raise SystemExit(f"FATAL: could not reach the database within 10s: {e}")

    try:
        # Sanity check: even though the query below uses exact membership
        # (`= ANY(...)`), not a wildcard, explicitly confirm no scenario_id
        # outside TARGET_SCENARIOS was matched, so a future edit to this
        # script can't silently widen it without tripping this check.
        rows = conn.execute(
            "SELECT DISTINCT scenario_id FROM sweep_runs WHERE scenario_id = ANY(%s)",
            (list(TARGET_SCENARIOS),),
        ).fetchall()
        found_ids = {r[0] for r in rows}
        unexpected = found_ids - set(TARGET_SCENARIOS)
        if unexpected:
            raise SystemExit(f"FATAL: unexpected scenario_id(s) matched: {unexpected}")

        per_scenario_counts = {}
        for sid in TARGET_SCENARIOS:
            c, _ = get_counts(conn, [sid])
            per_scenario_counts[sid] = c
            print(f"  {sid}: sweep_runs={c['sweep_runs']} memories={c['memories']} "
                  f"memory_influence={c['memory_influence']}")

        total_counts, trace_ids = get_counts(conn, list(TARGET_SCENARIOS))
        print(f"\nTotal across {len(TARGET_SCENARIOS)} scenarios: "
              f"sweep_runs={total_counts['sweep_runs']} ({len(trace_ids)} distinct trace_ids) "
              f"memories={total_counts['memories']} "
              f"memory_influence={total_counts['memory_influence']}")

        if not args.apply:
            print("\nDry run only (no --apply passed). Nothing deleted.")
            return

        if total_counts["sweep_runs"] == 0:
            print("\nNothing to delete -- no sweep_runs rows found for these scenarios. Exiting.")
            return

        snapshot_dir = write_snapshot(total_counts, per_scenario_counts)
        print(f"\nSnapshot written to {snapshot_dir}")

        print("Deleting in a single transaction (memory_influence -> memories -> sweep_runs)...")
        conn.autocommit = False
        try:
            conn.execute("DELETE FROM memory_influence WHERE trace_id = ANY(%s)", (trace_ids,))
            conn.execute("DELETE FROM memories WHERE scenario_id = ANY(%s)", (list(TARGET_SCENARIOS),))
            conn.execute("DELETE FROM sweep_runs WHERE scenario_id = ANY(%s)", (list(TARGET_SCENARIOS),))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit = True

        print("Delete committed.")
        print("\nNext steps (NOT run by this script -- these cost real Azure API calls):")
        print("  python eval/run_full_sweep.py --launch --workers 3 --max-attempts 5")
        print("  python eval/label_full_corpus.py --launch --workers 3")
        print("  python eval/compute_clean_control_metrics.py")
        print("  python eval/make_figures.py")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
