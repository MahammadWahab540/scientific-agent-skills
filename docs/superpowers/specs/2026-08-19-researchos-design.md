# ResearchOS Core Design

## Purpose

Add a fork-specific autonomous-research operating layer above the existing scientific Agent Skills repository without modifying the semantics or packaging of the upstream `skills/` collection.

## Required research loop

The system must represent this loop as real persisted software objects rather than a prompt-only workflow:

1. Research goal
2. Persistent knowledge graph
3. Evidence ledger
4. Hypothesis registry
5. Experiment registry
6. Decision engine
7. Agent orchestrator
8. Scientific Agent Skills capability resolution
9. Computational experiment
10. Independent critic
11. Physical experiment boundary
12. Measured evidence
13. Bayesian/confidence update
14. Next-best experiment

## Architecture

ResearchOS is a top-level Python package. It is intentionally not a `skills/researchos` skill because the upstream repository guidance excludes broad orchestrator skills. Existing skill files remain independently portable and usable by other Agent Skills hosts.

SQLite is the persistence layer because it is in the Python standard library, transactional, inspectable, and sufficient for the first single-node research engine. Typed tables store domain objects while `graph_nodes` and `graph_edges` provide a lightweight persistent property graph. An append-only `events` table records lifecycle changes.

## Components

### Domain models

`researchos.models` defines immutable dataclasses for research goals, evidence, hypotheses, experiments, experiment runs, critiques, and measurements. IDs are opaque prefixed UUIDs. Scientific probabilities and normalized scores validate their allowed ranges at construction.

### Persistent knowledge graph

`researchos.store.ResearchStore` owns SQLite schema creation and persistence. Every domain object is mirrored into `graph_nodes`; semantic relations such as `HAS_EVIDENCE`, `HAS_HYPOTHESIS`, `TESTED_BY`, `HAS_RUN`, `REVIEWED_BY`, `PRODUCED_MEASUREMENT`, and `UPDATES` are recorded in `graph_edges`.

### Registries

`EvidenceLedger`, `HypothesisRegistry`, and `ExperimentRegistry` provide bounded creation APIs and ensure graph links are written alongside relational records. Evidence can be linked to a hypothesis as supporting, challenging, or contextual without collapsing the evidence into the hypothesis claim.

### Decision engine

The decision engine ranks planned experiments, not hypotheses. The score combines expected information gain, feasibility, cost efficiency relative to the supplied budget, current hypothesis uncertainty, and a risk penalty. Over-budget experiments remain persisted but are not selected as executable candidates for that decision call.

### State machine

`ResearchStateMachine` encodes the intended scientific loop and rejects invalid transitions. The state machine is explicit rather than silently advanced by every CRUD call because real research is non-linear and users may ingest evidence or measurements out of sequence. The orchestrator exposes `advance_goal` to record deliberate state changes.

### Agent and skill orchestration

`SkillCatalog` discovers local Agent Skills by reading only the small top-level frontmatter fields required for routing. `AgentDispatcher` resolves every declared skill name before calling an adapter implementing `ScientificAgent`. No LLM vendor is hard-coded.

### Computational execution

A `ComputationalExecutor` adapter executes only experiments declared as computational. The orchestrator records run summary, artifacts, executor identity, status transitions, and graph edges. Exceptions mark the experiment failed and are re-raised.

### Physical experiment gate

ResearchOS never autonomously executes a physical experiment. Physical experiments can be planned and selected, but execution occurs under external human/laboratory controls. Measured results are subsequently ingested through `record_measurement`.

### Independent critic

Critiques are persisted first-class objects with verdict, issue list, and critic confidence. They link to the experiment through `REVIEWED_BY` and do not automatically alter hypothesis probability.

### Bayesian confidence update

Measurements carry an explicit positive likelihood ratio. Posterior odds are calculated as prior odds multiplied by the likelihood ratio. This prevents the system from silently converting subjective prose into a Bayesian update.

## Error handling

- Unknown IDs raise `KeyError` with the missing entity type.
- Invalid probability/risk/feasibility ranges raise `ValueError`.
- Invalid state transitions raise `ValueError`.
- Selecting with no feasible planned experiment raises `LookupError`.
- Missing declared skills fail before agent or executor dispatch.
- Computational executor exceptions persist `failed` status and propagate to the caller.
- Automatic physical execution raises `ValueError`; lab work must remain external.

## Security and scientific boundaries

The core does not fetch unpublished data, call remote databases, operate laboratory hardware, or infer clinical/scientific truth. Those actions belong to explicitly configured scientific skills and qualified external adapters. ResearchOS stores provenance and orchestration state but does not override the safety boundaries documented by each individual scientific skill.

## Testing

The dedicated suite under `tests/_researchos/` verifies Bayesian math, decision ranking, valid/invalid state transitions, local skill discovery, graph persistence, registry links, persistence across reopen, critique persistence, computational adapter execution, CLI initialization, and audit-ready goal snapshots. A dedicated GitHub Actions workflow runs the suite on ResearchOS changes.
