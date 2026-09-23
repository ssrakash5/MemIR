# MemoryIR

Post-incident blast-radius reconstruction for poisoned agent memory.
Research artifact accompanying a submission to IEEE SaTML 2027.

## What this is

Once a memory or source in an LLM agent's long-term memory is known to
be compromised, how accurately can execution provenance reconstruct
the downstream blast radius in a branching agent-memory derivation
graph, and what does containment cost as a function of retrieval
fan-out, derivation depth, and attribution policy?

We build a generation harness that produces branching derivation
graphs under controlled conditions across three LLMs (gpt-4o-mini,
gpt-4o, Llama-3.3-70B-Instruct), 30 synthetic scenarios (24 adversarial
across four poison-injection styles, 6 clean controls), yielding
21,570 generated traces and 216,319 labeled derived memories, plus a
20-document real-document validation slice testing which parts of the
result survive moving from synthetic scenarios to naturally occurring
source text. Full method, results, and limitations are in
`docs/paper/`.

## Repository layout

```
configs/
  experiment_grid.yaml      frozen experimental design (dated decisions recorded inline)
  scenarios/                30 synthetic scenario specifications (24 poisoned + 6 clean_control)
  scenarios/real_documents/ 20 real-document validation scenarios

real_documents/              frozen source documents + provenance manifest for the RD slice

src/memoryir/                 core library: db, embeddings, harness, labeler, metrics, scenarios

eval/                         generation, labeling, and analysis scripts (see eval/README.md)

tests/                        fixture tests for the metrics module

results/
  metrics/                    summary CSVs for H1-H4 (regenerable)
  figures/                    paper figures (regenerable)
  real_document_validation/   RD-slice summary tables + manual-review file
  full_sweep/                 run provenance (git commit + config snapshot per launch)

docs/
  preregistration.md          pre-registered hypotheses, metrics, and design (stamped before generation)
  labeling_protocol.md        ground-truth labeling rubric and pipeline
  corpus_card.md               corpus statistics and reproducibility pointers
  data_validation.md          post-hoc data-quality checklist
  paper/                       paper source (Markdown drafts + docs/paper/latex/ for the LaTeX build)
```

## Reproducing the results

Requires a running Postgres instance with `pgvector` (`memoryir-pg` in
the setup this was developed against), API access to the model
endpoints used (Azure OpenAI for gpt-4o-mini/gpt-4o, Azure AI Foundry
for Llama-3.3-70B-Instruct — see `src/memoryir/llm.py` for the exact
environment variables expected, conventionally read from a
`creds.env` file kept outside the repository), and:

```bash
pip install -e ".[eval]"
```

Full pipeline (`eval/README.md` has the complete walkthrough):

```bash
# 1. Sanity-check the enumeration before touching the DB/API (no cost)
python eval/run_full_sweep.py --dry-run

# 2. Generate (resumable; checkpointed per trace_id)
python eval/run_full_sweep.py --launch

# 3. Label every derived memory against its scenario's ground truth
python eval/label_full_corpus.py --launch

# 4. Compute H1-H4 metrics + bootstrap CIs
python eval/compute_metrics.py
python eval/compute_h2_metrics.py
python eval/compute_h3_metrics.py
python eval/compute_h4_metrics.py
python eval/bootstrap_h1.py && python eval/bootstrap_h2_h3_h4.py

# 5. Regenerate figures
python eval/make_figures.py
```

The real-document validation slice (`eval/run_real_document_validation.py`,
`eval/label_real_document_validation.py`,
`eval/compute_real_document_metrics.py`) and the two robustness checks
(`eval/compute_h2_second_embedding_robustness.py`,
`eval/compute_h4_window_sensitivity.py`) follow the same
generate-then-label-then-analyze pattern and are independently runnable
once the main corpus exists.

Raw generated memories, embeddings, and labels live in Postgres and
are not git-tracked (regenerable from the above given API access);
summary CSVs and figures are released for convenience so results can
be checked without regenerating the full corpus. See
`docs/paper/open_science.md` for the exact list of what is released
versus regenerable, and `docs/corpus_card.md` for corpus statistics.

## License

MIT — see `LICENSE`.
