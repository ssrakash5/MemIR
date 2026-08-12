"""Draw the blind human-annotation sample for kappa validation.

Stratifies 6 memories per (poison_form x depth) cell -- 4 poison forms x
5 depths = 20 strata x 6 = 120 total, within docs/labeling_protocol.md's
100-150 target range. Writes two files to results/kappa_sample/:
  - blind_annotation_sheet.csv: sample_id, semantic_target,
    candidate_memory, blank your_label column -- this is what a human
    annotator sees.
  - answer_key_DO_NOT_OPEN_UNTIL_DONE.csv: sample_id -> real memory_id,
    scenario_id, poison_form, depth, branch, derivation_transform --
    for scoring against the automated pipeline's output later. Do not
    open until blind labeling is complete.

Usage:
    python eval/draw_kappa_sample.py [--n-per-stratum 6] [--seed 42]
"""
import argparse
import csv
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import psycopg

from memoryir.scenarios import load_all_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-stratum", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--database-url",
        default="postgresql://postgres:memoryir@localhost:5433/memoryir",
    )
    parser.add_argument(
        "--out-dir", default=str(REPO_ROOT / "results" / "kappa_sample")
    )
    args = parser.parse_args()

    specs = load_all_scenarios(REPO_ROOT / "configs" / "scenarios")
    target_by_scenario = {
        s["scenario_id"]: s["semantic_target"]["definition"].strip() for s in specs
    }

    conn = psycopg.connect(args.database_url, autocommit=True)
    rows = conn.execute(
        """
        SELECT id, scenario_id, trace_id, depth, branch, derivation_transform, content
        FROM memories WHERE branch IN ('child_1','child_2')
        """
    ).fetchall()

    by_stratum: dict[tuple[str, int], list] = {}
    for r in rows:
        _, scenario_id, _, depth, _, _, _ = r
        poison_form = scenario_id.rsplit("_", 1)[0]
        by_stratum.setdefault((poison_form, depth), []).append(r)

    rng = random.Random(args.seed)
    sample = []
    for key in sorted(by_stratum):
        pool = list(by_stratum[key])
        rng.shuffle(pool)
        sample.extend(pool[: args.n_per_stratum])
    rng.shuffle(sample)

    print(f"Drew {len(sample)} memories across {len(by_stratum)} strata "
          f"({args.n_per_stratum} per stratum).")

    blind_rows, key_rows = [], []
    for i, (mid, scenario_id, trace_id, depth, branch, transform, content) in enumerate(
        sample, start=1
    ):
        sample_id = f"S{i:03d}"
        blind_rows.append(
            {
                "sample_id": sample_id,
                "semantic_target": target_by_scenario[scenario_id],
                "candidate_memory": content,
                "your_label": "",
            }
        )
        key_rows.append(
            {
                "sample_id": sample_id,
                "memory_id": mid,
                "scenario_id": scenario_id,
                "poison_form": scenario_id.rsplit("_", 1)[0],
                "trace_id": trace_id,
                "depth": depth,
                "branch": branch,
                "derivation_transform": transform,
            }
        )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    blind_path = out_dir / "blind_annotation_sheet.csv"
    with open(blind_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["sample_id", "semantic_target", "candidate_memory", "your_label"]
        )
        w.writeheader()
        w.writerows(blind_rows)

    key_path = out_dir / "answer_key_DO_NOT_OPEN_UNTIL_DONE.csv"
    with open(key_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id", "memory_id", "scenario_id", "poison_form",
                "trace_id", "depth", "branch", "derivation_transform",
            ],
        )
        w.writeheader()
        w.writerows(key_rows)

    print(f"Wrote {blind_path}")
    print(f"Wrote {key_path} (do not open until labeling is done)")


if __name__ == "__main__":
    main()
