"""Blast-radius metrics, matching the canonical definitions in
docs/preregistration.md ("Metric definitions" section) exactly.

B_true is anchored to semantic contamination (content_label == CARRIES),
not structural reachability -- this module never uses content_label to
decide what a detector FLAGS (that would leak ground truth into the
detector), only to decide what counts as truly contaminated when scoring
a policy's flagged set against it.

Two flagging policies computed here (H1's core comparison, no attribution
score needed):
  - structural: forward-reachable from the compromised root via
    STRUCTURAL_PARENT edges only (TRUE_DESCENDANT reachability)
  - context_exposure: forward-reachable via STRUCTURAL_PARENT OR
    CO_RETRIEVED edges (conservative propagation)

Traversal is plain BFS over an in-memory adjacency list (not a live SQL
recursive CTE) -- cycle-safe by construction via a visited-set, verified
against a deliberately cyclic fixture in tests/test_metrics.py per
week2.md's explicit cycle-termination requirement.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TraceGraph:
    """nodes: id -> {depth, branch, content_label}. edges: list of
    (parent_id, child_id, role)."""
    nodes: dict[int, dict]
    edges: list[tuple[int, int, str]]
    root_id: int


def build_adjacency(edges: list[tuple[int, int, str]], allowed_roles: set[str]) -> dict[int, list[int]]:
    adj: dict[int, list[int]] = {}
    for parent_id, child_id, role in edges:
        if role in allowed_roles:
            adj.setdefault(parent_id, []).append(child_id)
    return adj


def reachable_from(root_id: int, adj: dict[int, list[int]]) -> set[int]:
    """BFS forward reachability. Visited-set guarantees termination even
    on a cyclic graph (verified in tests/test_metrics.py) -- does not
    depend on the DAG-by-construction assumption holding."""
    visited: set[int] = set()
    queue = [root_id]
    while queue:
        cur = queue.pop()
        for nxt in adj.get(cur, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def b_true(graph: TraceGraph, *, max_depth: int) -> set[int]:
    """Semantic-contamination ground truth: every derived memory (depth
    >= 1, depth <= max_depth) labeled CARRIES. Does NOT traverse edges --
    content_label already captures whatever contamination actually
    occurred, structural or incidental (worked example 8)."""
    return {
        nid for nid, n in graph.nodes.items()
        if n["content_label"] == "CARRIES" and 1 <= n["depth"] <= max_depth
    }


def b_flagged(graph: TraceGraph, *, policy: str, max_depth: int) -> set[int]:
    """A policy's flagged set -- computed WITHOUT looking at content_label
    (a real detector doesn't have ground truth), only graph structure."""
    allowed = {"structural": {"STRUCTURAL_PARENT"},
               "context_exposure": {"STRUCTURAL_PARENT", "CO_RETRIEVED"}}[policy]
    adj = build_adjacency(graph.edges, allowed)
    reached = reachable_from(graph.root_id, adj)
    return {nid for nid in reached if graph.nodes.get(nid, {}).get("depth", 0) <= max_depth
            and graph.nodes[nid]["depth"] >= 1}


def blast_radius_metrics(graph: TraceGraph, *, policy: str, max_depth: int) -> dict:
    """Returns P_BR, R_BR, inflation_ratio per docs/preregistration.md's
    canonical definitions. N/A (None) when B_true is empty, per the
    preregistered depth=0/empty-blast-radius handling rule -- never
    coerced to zero."""
    bt = b_true(graph, max_depth=max_depth)
    bf = b_flagged(graph, policy=policy, max_depth=max_depth)
    inter = bt & bf
    if len(bt) == 0:
        return {"P_BR": None, "R_BR": None, "inflation_ratio": None,
                "b_true_n": 0, "b_flagged_n": len(bf)}
    return {
        "P_BR": (len(inter) / len(bf)) if bf else 0.0,
        "R_BR": len(inter) / len(bt),
        "inflation_ratio": (len(bf) / len(bt)),
        "b_true_n": len(bt),
        "b_flagged_n": len(bf),
    }
