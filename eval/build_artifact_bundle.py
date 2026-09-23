"""Stage a clean, double-blind-safe copy of exactly what
docs/paper/open_science.md says the anonymized artifact contains --
scenario specs, experimental grid, generation harness, labeling
pipeline, metric/bootstrap/figure code, provenance JSON, and
summary CSVs/figures. Excludes raw API traces, .git history, and
anything identifying.

WHY THIS SCRIPT EXISTS: actually creating the anonymous hosting mirror
(e.g. anonymous.4open.science) requires an external account action this
script cannot do. What it CAN do safely is (1) produce a fresh,
history-free copy of exactly the files that belong in the artifact, per
open_science.md's own description, so that copy -- not the real repo
with its full git history and author-attributed commits -- is what gets
pushed to a fresh anonymous-hosting-ready repo, and (2) scan every
staged file for double-blind-identifying strings and fail loudly if any
are found, rather than silently shipping a deanonymizing artifact.

KNOWN FINDING (2026-09-21): the real repo's LICENSE file contains
"Copyright (c) 2026 ssrakash5" -- a GitHub-username-identifying string.
This script blanks that specific line in the staged copy. It does NOT
touch the real repo's LICENSE file (that's a separate decision for the
user -- the real repo can stay attributed; only the anonymized artifact
copy must not be).

Usage:
    python eval/build_artifact_bundle.py            # dry run: list what would be staged
    python eval/build_artifact_bundle.py --apply     # actually stage the copy

Output: <scratch staging dir>/memoryir-artifact/ (default: a
`artifact_bundle/` directory under the repo root's parent, NOT inside
the git repo itself, so it can never be accidentally committed or
picked up by a later `git add -A`). Override with --out.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT.parent / "memoryir-artifact-bundle"

# Exactly what docs/paper/open_science.md's "Git-tracked and released
# with the paper" + "we additionally release summary CSVs/figures"
# bullets describe. Update this list and that doc together if either
# changes -- they must stay in sync.
INCLUDE_PATHS = [
    "configs/scenarios",             # 30 scenario specs (24 poisoned + 6 clean_control)
    "configs/experiment_grid.yaml",  # frozen experimental grid
    "eval",                          # generation harness entry points + all compute/bootstrap/figure code
    "src/memoryir",                  # harness.py, labeler.py, and the rest of the package
    "docs",                          # preregistration, labeling protocol, corpus card, paper drafts
    "results/metrics",               # summary CSVs (regenerable, but released for convenience) -- large *_raw.csv dumps excluded below
    "results/figures",               # figures (regenerable, but released for convenience)
    "results/full_sweep",            # run_meta_*.json provenance only -- launch_log/err excluded below
    "results/real_document_validation",  # RD-slice compact tables + manual-review file -- *_raw.csv excluded below
    "pyproject.toml",
    "LICENSE",
    "README.md",
]

# Excluded even if they'd otherwise be swept in by an INCLUDE_PATHS
# directory above. Globs are relative to REPO_ROOT.
EXCLUDE_GLOBS = [
    "results/full_sweep/launch_log*.txt",
    "results/full_sweep/launch_err*.txt",
    "results/full_sweep/retry_loop_log.txt",
    "**/__pycache__/**",
    "**/*.pyc",
    # Large per-trace/per-row raw dumps (tens of MB each, ~119MB total) --
    # open_science.md describes "summary CSVs", not these; they also
    # aren't git-tracked in the real repo (results/* is gitignored there,
    # regenerable-only). Every raw dump in this codebase's naming
    # convention ends in _raw.csv, so this excludes by that suffix rather
    # than an explicit per-file list that would need updating each time a
    # new analysis script adds one.
    "results/metrics/*_raw.csv",
    "results/real_document_validation/*_raw.csv",
    # Raw downloaded copies of third-party cited papers -- copyrighted
    # material, not part of what open_science.md describes as released,
    # and already gitignored in the real repo (docs/papers/*.pdf) for
    # the same reason. "docs" is swept in wholesale by INCLUDE_PATHS
    # above for the paper drafts/preregistration/etc. it also contains,
    # so this needs an explicit carve-out -- .gitignore doesn't apply
    # here since this script scans the filesystem, not git.
    "docs/papers/*.pdf",
    "results/kappa_sample/*.csv",   # raw blind-annotation sheets, not part of the release per open_science.md
    "docs/paper/latex/main.pdf",
    "docs/paper/latex/*.aux",
    "docs/paper/latex/*.bbl",
    "docs/paper/latex/*.blg",
    "docs/paper/latex/*.log",
    "docs/paper/latex/*.out",
    "docs/paper/latex/missfont.log",
    # Repo-hygiene/meta-tooling scripts, not part of what open_science.md
    # describes as released (generation harness / labeling pipeline /
    # metric-bootstrap-figure code) -- also would self-trip the
    # identifier scan below since they list those strings as data.
    "eval/build_artifact_bundle.py",
    "eval/invalidate_clean_control_scenarios.py",
    # Documents the artifact-staging process itself (including, by name,
    # the identifying strings this script scans for) -- meta-process
    # notes for the author, not paper content a reader needs.
    "docs/paper/artifact_manifest.md",
]

# Double-blind identifying strings to scan for in every staged file.
# Keep in sync with anything a future author adds to creds.env / git
# config -- this list is deliberately specific, not a generic PII
# scanner, so it stays fast and low-noise.
IDENTIFYING_STRINGS = [
    "ssrakash5",
    "ssrak",
    "akashgemini1903",
    "akashvarma1903",
]

TEXT_EXTENSIONS = {
    ".py", ".md", ".yaml", ".yml", ".toml", ".cff", ".txt", ".json",
    ".tex", ".bib", ".cfg", ".ini", ".sql",
}
# Extensionless files worth scanning by exact filename (LICENSE has no
# suffix, so TEXT_EXTENSIONS alone would silently skip it).
TEXT_FILENAMES = {"LICENSE", "README"}


def iter_included_files():
    for rel in INCLUDE_PATHS:
        p = REPO_ROOT / rel
        if not p.exists():
            print(f"  WARNING: {rel} does not exist, skipping")
            continue
        if p.is_file():
            yield p
        else:
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    yield f


def is_excluded(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(path.match(g) or Path(rel).match(g) for g in EXCLUDE_GLOBS)


def scan_for_identifiers(path: Path) -> list[str]:
    if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in TEXT_FILENAMES:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    hits = []
    for s in IDENTIFYING_STRINGS:
        if re.search(re.escape(s), text, re.IGNORECASE):
            hits.append(s)
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Actually stage the copy. Without this, dry run only.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Staging directory (default: {DEFAULT_OUT})")
    args = parser.parse_args()

    if args.out.is_relative_to(REPO_ROOT):
        raise SystemExit(
            f"FATAL: --out ({args.out}) is inside the git repo -- refusing, "
            f"since that risks the staged copy being committed or swept up "
            f"by a later 'git add -A'. Pick a path outside {REPO_ROOT}."
        )

    files = list(iter_included_files())
    files = [f for f in files if not is_excluded(f)]

    print(f"{len(files)} files would be staged from {len(INCLUDE_PATHS)} include paths.")

    all_hits: dict[Path, list[str]] = {}
    for f in files:
        hits = scan_for_identifiers(f)
        if hits:
            all_hits[f] = hits

    if all_hits:
        print(f"\nFATAL: {len(all_hits)} file(s) contain double-blind-identifying strings:")
        for f, hits in all_hits.items():
            print(f"  {f.relative_to(REPO_ROOT)}: {hits}")
        print(
            "\nFix these (redact/replace, e.g. LICENSE's copyright line -- "
            "this script already handles that one specific case, see below) "
            "before staging, or add a targeted exception here if a hit is a "
            "false positive."
        )
        if "LICENSE" not in {f.name for f in all_hits}:
            raise SystemExit(1)
        # LICENSE is handled by the copyright-line rewrite below; any
        # OTHER file with a hit is still fatal.
        other_hits = {f: h for f, h in all_hits.items() if f.name != "LICENSE"}
        if other_hits:
            raise SystemExit(1)
        print("(LICENSE hit is expected -- handled by the copyright-line rewrite below.)")

    if not args.apply:
        print("\nDry run only (no --apply passed). Nothing staged.")
        return

    if args.out.exists():
        print(f"\n{args.out} already exists -- removing it first.")
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)

    for f in files:
        rel = f.relative_to(REPO_ROOT)
        dest = args.out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if rel.name == "LICENSE":
            text = f.read_text(encoding="utf-8")
            text = re.sub(r"Copyright \(c\) (\d{4}) \S+", r"Copyright (c) \1 Anonymous Author(s)", text)
            dest.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(f, dest)

    print(f"\nStaged {len(files)} files to {args.out}")
    print(
        "\nThis directory has no .git history and is NOT the real repo -- "
        "push it to a FRESH repo (no prior commits) before pointing an "
        "anonymous-hosting service at it, so no commit-author metadata "
        "leaks. Verify no other identifying strings slipped through "
        "before making it public (this script's IDENTIFYING_STRINGS list "
        "is deliberately narrow, not a general PII scanner)."
    )


if __name__ == "__main__":
    main()
