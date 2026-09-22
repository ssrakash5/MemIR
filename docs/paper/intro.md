<!-- DRAFT — Markdown first, per 2026-08-14 decision. Rough is fine;
complete is not optional (week6.md). Convert to LaTeX once reviewed and
the SaTML template is available. -->

# Introduction

Large language model (LLM) agents increasingly persist information
across sessions in an explicit memory store — a vector database or
structured log that the agent writes to after completing tasks and
retrieves from on future turns. This gives agents continuity: they can
recall prior decisions, user preferences, and task context without
re-deriving them each session. It also creates a new attack surface.
Persistent-memory poisoning — where an attacker gets a false or harmful
claim written into an agent's long-term memory, typically not by
directly editing the memory store but by influencing content the agent
processes and subsequently writes about — is now an established
cross-session agent security problem, distinct from single-turn prompt
injection precisely because the compromised state outlives the
triggering interaction. OWASP's Agentic Security Initiative names this
failure mode explicitly (Memory Poisoning, threat ID T1 in its
Agentic AI Threats and Mitigations guide); recent work (MemLineage, MemAudit,
MemSecBench, MPBench, AgentPoison, MINJA — see Related Work) has moved
the subfield from essentially nothing to active study within months.

The mechanism that makes persistent-memory poisoning qualitatively
different from a single bad response is **derivation**: an agent's
memories are not static records. An agent may summarize, paraphrase,
refine, or continue prior memories when producing new ones, retrieving
several existing memories and writing one or more new memories that
draw on that retrieved context. A single compromised memory can
therefore become the ancestor of an entire branching subgraph of later
writes, some of which may carry the original harmful claim forward
(sometimes verbatim, sometimes reworded beyond simple string matching)
and some of which may not. Once an operator discovers that *one*
memory is compromised — through an anomaly report, an incident
investigation, or a security scan — the operational question is no
longer "was this one memory malicious," but **"what else, downstream,
needs to be treated as exposed, and what is the cost of finding out."**

This is a different question from the ones existing memory-security
work answers. MemLineage builds a preventive lineage graph and gates
sensitive actions in real time, before a harmful outcome occurs, mostly
evaluated over linear derivation chains. MemAudit works after a harmful
event has already been *observed*, using counterfactual replay and
structural anomaly detection to rank suspicious memories for removal,
without maintaining persistent derivation provenance connecting a
known-compromised source to memories that have not yet caused visible
harm. Neither paper asks: given a memory that is now *known* to be
compromised — independent of whether it has caused a harmful action
yet — what is the actual shape and size of its downstream footprint in
a **branching** derivation graph, and what does it cost to contain?

We study **post-incident blast-radius reconstruction**: once a memory
or source is known to be compromised, how accurately can execution
provenance reconstruct the downstream blast radius in a branching
agent-memory graph, and what does containment cost, as a function of
retrieval fan-out, derivation depth, and attribution policy? We build a
generation harness that produces branching derivation graphs under
controlled conditions — a compromised source, a mix of true structural
dependents and merely co-retrieved distractors, varying retrieval
fan-out (`top_k`) and write fan-out per run — across three LLMs
(gpt-4o-mini, gpt-4o, Llama-3.3-70B-Instruct), 24 adversarial scenarios
spanning four distinct poison-injection styles plus 6 clean/unpoisoned
controls, and label every derived memory's actual semantic content
against its scenario's ground-truth target using a validated three-signal
automated labeler (Cohen's κ = 0.87–0.88 against blind human
annotation).

The central empirical tension we characterize is a **precision/recall
frontier**, not a single failure mode. Conservative provenance —
treating every memory retrieved into a write's context as a potential
influence, not just the ones the write's content structurally depends
on — preserves near-complete recall of true contamination but produces
a large number of false-positive flags, and that inflation grows with
retrieval fan-out and derivation depth (Section [Results], H1).
Thresholding attribution by confidence reduces that inflation, but at
a real, measurable recall cost: some semantic contamination reaches a
descendant write only through content that was merely co-retrieved
alongside a write's true structural parents, not through the
structural parent itself, and aggressive attribution thresholds prune
exactly that signal away (H2). We also find that the harmful claim's
distinctive surface form (its literal identifiers, account numbers, or
phrasing) can survive rewording much more reliably than a naive
"does the marker text still appear" check would suggest is guaranteed
— but not perfectly: at full corpus scale we observe a small but real
laundering rate (0.79%), concentrated in specific derivation
transforms and, notably, more pronounced for one of our three tested
models than the other two (H3). Finally, a depth-aware containment
policy that quarantines broadly near a compromise but requires
confirmed structural lineage further downstream measurably reduces
over-quarantine relative to a flat conservative policy, at a
quantifiable missed-contamination cost (H4).

**Contributions:**

1. A blast-radius reconstruction framework for branching agent-memory
   derivation graphs, with a three-layer ground-truth taxonomy
   (structural lineage, context exposure, semantic contamination) that
   makes the precision/recall frontier measurable rather than assumed.
2. An oracle-generation methodology for constructing scenarios with a
   programmatically-derived, human-approved ground truth — avoiding
   both hand-authoring every edge and letting an LLM decide its own
   ground truth after the fact — validated against blind human
   annotation (κ = 0.87–0.88).
3. A full factorial study (21,600 planned / 21,570 generated traces, 3 LLMs, 30
   scenarios including clean controls, 5 dependent variables) that
   characterizes the H1–H4 tradeoffs empirically, including two
   findings that revised our own pre-registered pilot expectations
   rather than confirming them: real (if rare) laundering at full
   scale, and a genuine cross-model asymmetry in how reliably surface
   markers survive derivation.
</content>
