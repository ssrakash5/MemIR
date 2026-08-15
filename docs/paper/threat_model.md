<!-- DRAFT — Markdown first. -->

# Threat Model

## Setting

An LLM agent maintains a persistent memory store across sessions. The
agent periodically **retrieves** a set of memories relevant to its
current context (e.g. by embedding similarity) and **writes** new
memories derived from that retrieved context — summarizing,
paraphrasing, refining, or continuing what it retrieved. A single
retrieval-and-write event (a "run") can produce more than one new
memory (write fan-out $> 1$): for example, an agent that processes one
retrieved batch of context and writes several distinct notes from it in
the same turn.

## What the attacker controls

The attacker does not require direct write access to the memory
database. Consistent with the threat models in MemLineage, MemSecBench,
and MINJA (Related Work), we assume the attacker can influence content
that legitimately enters the agent's write path — a web page, document,
tool output, or upstream message the agent processes during ordinary
operation — such that the agent's own, otherwise-normal write behavior
persists a harmful claim into memory. The attacker does not modify the
memory backend directly, does not require white-box access to the
retriever or model (distinguishing this from AgentPoison's threat
model), and does not require a shared memory bank across users
(distinguishing this from MINJA's primary threat model). We do not
model how the attacker gains the position to influence that input
content in the first place (session/account compromise, supply-chain
compromise of a tool, etc.) — that is out of scope, consistent with
MemSecBench's own scoping.

## The precondition this paper starts from

Unlike MemLineage (which asks whether a *still-unknown* poisoned label
survives to trigger a future sensitive action) or MemAudit (which
requires an already-*observed* harmful outcome to trigger
investigation), we start from a different, narrower precondition: **a
specific source or memory is now known to be compromised** —
discovered via an anomaly report, a security scan, an incident
investigation, or any other out-of-band signal. This is a realistic
operational moment: incident responders regularly learn "this document
was malicious" or "this data source was compromised" without yet
knowing which downstream state was affected by it. The question this
paper answers is what happens *after* that moment: given the
compromised root, what does an operator need to quarantine or
regenerate, and how accurately and cheaply can that be determined.

## What we assume trusted

- The memory store's read/write mechanics themselves (no direct
  database tampering).
- The LLM's derivation behavior is not itself adversarial — it follows
  its instructions faithfully; it is not trying to evade a detector. We
  do not model an LLM that deliberately launders content to defeat
  provenance tracking (a stronger, different threat than the one we
  study).
- The embedding model used for retrieval and for our own attribution-
  score analysis (H2) is not itself compromised or adversarially
  targeted (no embedding-space attack, unlike AgentPoison's
  trigger-optimization threat model).
- Retrieval is not manipulated at the infrastructure level (index
  poisoning, retriever backdoors) — only the *content* available to be
  retrieved is attacker-influenced.

## What we do not model

- How the attacker gains the position to inject content in the first
  place (matches MemSecBench's scoping).
- Multi-step or adaptive attacks that specifically target the
  provenance-reconstruction mechanism itself once an incident response
  begins (an attacker aware they've been detected, trying to evade
  blast-radius reconstruction).
- Cross-user or shared-memory-bank contamination (MINJA's primary
  threat model) — our scenarios are single-agent, single-memory-store.
- Model-weight-level backdoors or supply-chain compromise of the LLM
  itself (out of scope, matching MemLineage's own stated limitations).

## Why this precondition matters for the metrics

Because we start from a *known* compromised root, our dependent
variables are about reconstruction accuracy and cost, not detection.
Blast-radius precision/recall (Section [Method]) measure how well a
given provenance policy identifies the *actual* downstream semantic
contamination, given that the root is already flagged — a different
question from "can this system detect that poisoning occurred at all,"
which is the question MemLineage's ASR-to-zero and MemAudit's
attack-success-rate-reduction results answer.
</content>
