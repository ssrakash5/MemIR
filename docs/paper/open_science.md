<!-- Required by the SaTML 2027 checklist: an "Open Science" section
describing released artifacts, placed after the main results/limitations
and before the LLM-usage-considerations / references. Does not count
toward the page limit. Grounded only in what this repo actually tracks
(docs/corpus_card.md, eval/README.md) — no forward-looking claims about
infrastructure that doesn't exist. -->

# Open Science

We release the full experimental pipeline needed to regenerate this
corpus and every reported result, not only a static data dump.

**Git-tracked and released with the paper:** the 30 human-approved
synthetic scenario specifications (24 poisoned across four
`poison_form` styles, 6 clean controls), the frozen experimental grid
(`configs/experiment_grid.yaml`), the generation harness
(`eval/run_full_sweep.py`, `src/memoryir/harness.py`), the labeling
pipeline (`src/memoryir/labeler.py`), and all metric/bootstrap/figure
code (`eval/compute_*.py`, `eval/bootstrap_*.py`, `eval/make_figures.py`).
The 20-scenario real-document validation slice is released the same
way: its scenario specifications (`configs/scenarios/real_documents/`),
frozen source-document manifest with SHA-256 hashes
(`real_documents/manifest.yaml`), generation and labeling runners
(`eval/run_real_document_validation.py`,
`eval/label_real_document_validation.py`), metric script
(`eval/compute_real_document_metrics.py`), and compact results tables
and manual-review file (`results/real_document_validation/`). Every
generation run's provenance (git commit, full config snapshot) is
recorded in `results/full_sweep/run_meta_*.json` (main corpus) and
`results/real_document_validation/run_meta_*.json` (real-document
slice).

**Not git-tracked, but regenerable from the above:** the raw generated
memories, embeddings, and labels (216,319 derived memories across 3
models for the main corpus; 2,400 for the real-document slice), which
live in Postgres. Given API access to the same three model endpoints
(gpt-4o-mini, gpt-4o, Llama-3.3-70B-Instruct, using the API versions
reported in Method) and the released scenario specs and grid, the
corpus is regenerable end to end via the seven-step pipeline documented
in `eval/README.md`, using the released pipeline and pinned API
versions; exact byte-identical outputs are not guaranteed, since
hosted-model inference at temperature 0 is not itself guaranteed to be
deterministic across requests or over time. We additionally release
summary CSVs (`results/metrics/`, `results/real_document_validation/`)
and figures (`results/figures/`) so results can be checked without
regenerating the full corpus.

**Missing data is documented, not hidden.** 30 of 21,600 planned
traces (0.14%) are permanently missing — all Llama-3.3-70B-Instruct,
rejected by the platform's content-safety filter — and are left as
genuine missing data rather than imputed; see `docs/corpus_card.md`.

**Anonymized artifact.** This submission is accompanied by an
anonymized artifact (TODO: insert anonymous-hosting link, e.g. an
anonymous.4open.science mirror, before submission — see
`docs/paper/latex/README.md`) containing the scenario specifications
(both the 30-scenario synthetic corpus and the 20-scenario
real-document slice), generation grid, harness code, labeling pipeline,
metric/bootstrap/figure code, and summary CSVs/figures listed above,
stripped of author-identifying commit history and deployment-specific
identifiers. It does not include raw API traces, to avoid
re-identifying the exact model deployment. Per the SaTML checklist's
post-submission update window (deadline 2026-10-02), we will keep that
artifact current through that date. Full de-anonymized release,
including a permanent repository URL and completed `CITATION.cff`,
follows acceptance.

**What we do not release.** Raw model credentials and any
API-key-bearing logs are redacted at generation time (per this
project's standing logging policy) and never included in any release.
