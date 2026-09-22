"""Generate real derived-memory traces for labeling validation.

Scope: runs every approved scenario under
configs/scenarios/ (24 total) through the harness to max_depth=5, at a
fixed top_k/write_fanout, across a small set of derivation_transform
values -- enough real output to build the remaining labeling worked
examples and draw the 100-150-memory kappa validation sample. This is
NOT the full production sweep over configs/experiment_grid.yaml's
generation_factors.

Usage:
    python eval/run.py
    python eval/run.py --transforms summarize paraphrase --top-k 5
"""
import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from memoryir import db
from memoryir.embeddings import Embedder
from memoryir.harness import TraceConfig, generate_trace
from memoryir.llm import LLMClient
from memoryir.scenarios import load_all_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--write-fanout", type=int, default=2, choices=[1, 2])
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--transforms",
        nargs="+",
        default=["summarize", "paraphrase"],
        choices=["summarize", "paraphrase", "refine", "continue"],
    )
    parser.add_argument("--scenarios-dir", default=str(REPO_ROOT / "configs" / "scenarios"))
    args = parser.parse_args()

    print("Loading approved scenarios...")
    specs = load_all_scenarios(Path(args.scenarios_dir))
    print(f"  {len(specs)} scenarios loaded and validated.")

    print("Loading embedding model...")
    embedder = Embedder()
    print(f"  dim={embedder.dim}")

    print("Connecting to Postgres + initializing LLM client...")
    conn = db.connect(embed_dim=embedder.dim)
    llm = LLMClient()

    total_traces = len(specs) * len(args.transforms)
    print(f"\nGenerating {total_traces} traces "
          f"({len(specs)} scenarios x {len(args.transforms)} transforms, "
          f"top_k={args.top_k}, write_fanout={args.write_fanout}, max_depth={args.max_depth})...\n")

    t_start = time.time()
    trace_ids = []
    n = 0
    for spec in specs:
        for transform in args.transforms:
            n += 1
            config = TraceConfig(
                top_k=args.top_k,
                write_fanout=args.write_fanout,
                derivation_transform=transform,
                seed=args.seed,
                max_depth=args.max_depth,
            )
            t0 = time.time()
            trace_id = generate_trace(spec, config, conn, llm, embedder)
            trace_ids.append(trace_id)
            print(f"  [{n}/{total_traces}] {trace_id}  ({time.time() - t0:.1f}s)")

    elapsed = time.time() - t_start
    n_memories = conn.execute(
        "SELECT count(*) FROM memories WHERE trace_id = ANY(%s)", (trace_ids,)
    ).fetchone()[0]
    n_derived = conn.execute(
        "SELECT count(*) FROM memories WHERE trace_id = ANY(%s) AND branch IN ('child_1','child_2')",
        (trace_ids,),
    ).fetchone()[0]

    print(f"\nDone in {elapsed:.1f}s. {len(trace_ids)} traces, "
          f"{n_memories} memory rows total ({n_derived} derived, rest are "
          f"depth-0 source facts/distractors).")
    print(f"\nDerived-memory pool ({n_derived} rows) is now available for "
          f"docs/labeling_protocol.md's remaining worked examples and the "
          f"kappa validation sample.")

    conn.close()


if __name__ == "__main__":
    main()
