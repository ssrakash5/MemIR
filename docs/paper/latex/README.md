# LaTeX conversion — status (2026-09-09)

Converted from `docs/paper/*.md` per the SaTML 2027 checklist/CFP
(verified live 2026-09-09 at `satml.org/call-for-papers/` and
`.../checklist/`). Compile `main.tex` with `pdflatex` + `bibtex`
(standard two-pass + bibtex + two-pass cycle).

**Compile-verified 2026-09-09** (TinyTeX, `IEEEtran`+`cite`+`courier`
packages installed via `tlmgr`): `pdflatex main.tex` → `bibtex main` →
`pdflatex main.tex` ×2 produces a clean 11-page `main.pdf`, zero LaTeX
errors, zero undefined references, zero font warnings. Build artifacts
(`*.aux/.bbl/.blg/.log/.out`, `main.pdf`) are gitignored, not committed
— regenerate with the same 4-command sequence. Requires
`results/figures/*.png` to exist first (`python eval/make_figures.py`
from repo root) or the `\includegraphics` calls in
`sections/results.tex` will fail.

## Template compliance (do not touch)

`\documentclass[conference]{IEEEtran}` at default 10pt, IEEE two-column
conference format. The checklist states modifying font size, margins,
or spacing is grounds for desk rejection — nothing in `main.tex` does
this; keep it that way.

## What's converted

`sections/{abstract,intro,threat_model,related_work,method,results,
limitations,open_science,ethical_considerations}.tex` — direct
conversion of the corresponding `docs/paper/*.md` files (`abstract.md`,
`open_science.md`, `ethical_considerations.md` are new, drafted
2026-09-09; see CLAUDE.md). `results.tex` also folds in bootstrap-CI
numbers for H2–H4 that `docs/paper/results.md` was missing (that file
has been updated to match). The `21,600 generated` vs. `21,570
generated` inconsistency an external review caught (contributions list
said "generated" for the planned count) is fixed in both `intro.md`
and `sections/intro.tex` — now reads "21,600 planned / 21,570
generated".

## Bibliography — verified 2026-09-09, re-verified 2026-09-21, real entries in `refs.bib`

All six cited works' titles and full author lists were fetched
directly from their arXiv abstract pages (not copied from a secondhand
summary) and are now in `refs.bib`: MemLineage (2605.14421), MemAudit
(2605.23723), MemSecBench (2607.27080), MPBench (2606.04329v2),
AgentPoison (2407.12784), MINJA (2503.03704).

**2026-09-21 submission-window re-check** (per this file's own earlier
"re-verify close to submission" flag):
- MINJA (arXiv 2503.03704) re-fetched: title confirmed still "Memory
  Injection Attacks on LLM Agents via Query-Only Interaction" as of
  v5 (2026-02-12), unchanged since the 2026-09-09 check. No action
  needed.
- OWASP ASI06 code: **corrected, was wrong.** The full 53-page guide
  PDF (https://genai.owasp.org/download/45674/) was downloaded and
  text-extracted directly this time (not just the landing page). The
  code "ASI06," previously cited in `intro.tex`/`related_work.tex`,
  does not appear anywhere in the document. The guide's actual code
  for cross-session memory poisoning, used consistently in its
  Detailed Threat Model table and Example Threat Models section, is
  **"T1" (Memory Poisoning)**. All four in-text citations
  (`intro.md`/`related_work.md`/`intro.tex`/`related_work.tex`) and
  the `refs.bib` note have been updated to cite T1 instead of the
  incorrect ASI06. This was never a numbered item below, just a
  bibliography caveat — now resolved and removed from that caveat
  list.

## What's NOT done — before this can be submitted

1. **Figures referenced by relative path** (`results/figures/*.png` in
   `sections/results.tex`) **are git-ignored/regenerable, not
   committed.** Run `python eval/make_figures.py` from the repo root
   before compiling, or the `\includegraphics` calls will fail.
2. **No actual anonymous artifact repository exists yet.**
   `open_science.tex`/`open_science.md` describe what the artifact
   contains and say it accompanies the submission, with an explicit
   `TODO: insert anonymous-hosting link` marker — an anonymous mirror
   (e.g. anonymous.4open.science) must actually be created and linked
   before that text is true. Do this before the 2026-09-29 deadline,
   not after. **Staging is now done** (2026-09-21): `eval/build_artifact_bundle.py`
   produces a clean, double-blind-scanned, history-free copy of exactly
   what `open_science.md` describes — see `docs/paper/artifact_manifest.md`
   for status and the one real finding it caught (`LICENSE` leaked the
   GitHub username; handled). Pushing that staged copy to a fresh repo
   and pointing an anonymizing service at it is still a manual step only
   the user can do.
3. **No Discussion section.** Not drafted (see CLAUDE.md status
   summary). **Appendix is now drafted** (2026-09-21,
   `sections/appendix.tex`, `\input` after `\bibliography` with a
   `\onecolumn`/`\twocolumn` switch since its full per-depth H1–H4
   tables use `longtable`): full per-depth H1/H2/H3/H4 breakdowns (main
   body only shows depth 1/5 summaries), the full experimental grid,
   the seed-diversity finding, and one worked labeling example.
   Compile-verified 2026-09-21: 0 errors, 0 undefined refs, 0 warnings
   from the new content (5 pre-existing overfull-hbox warnings in
   `results.tex` are unrelated, not introduced by this addition); PDF
   is now 16 pages total (appendices don't count against the 12-page
   body limit). Abstract, Open Science, Ethical Considerations, and
   now Appendix are drafted; Discussion is the only section still
   missing.
4. **LLM-usage-considerations section still deliberately absent.**
   Required by the checklist — the user is writing it themselves
   (explicit instruction, 2026-09-09). Add
   `\input{sections/llm_usage}` in `main.tex` (marked with a comment
   where it goes) once that file exists, before `\bibliography`.
5. **Double-blind check was done at the Markdown/prose stage only** —
   re-check the compiled PDF once Discussion lands, since a
   reference to prior own work must stay third-person.
6. **Model/embedding/judge version table not added.** An external
   review flagged that the paper should state exact model
   snapshot/API version, temperature, embedding model version, and
   judge model version in a small experimental-details table. The
   exact deployment/API-version strings live in untracked env vars
   (`creds.env`, per `src/memoryir/llm.py`), not in the repo — decide
   with the user which of those strings are safe to disclose without
   breaking double-blind anonymity (Azure deployment names can be
   institution-identifying) before adding this table.
7. **ORCID + Author Certification deadline is 2026-09-22** — separate
   from and earlier than the 2026-09-29 paper deadline, not a LaTeX
   task but easy to miss.
