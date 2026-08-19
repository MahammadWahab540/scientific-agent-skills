# ResearchOS Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent ResearchOS loop above the scientific Agent Skills library, from research goal through next-best experiment selection.

**Architecture:** Keep `skills/` unchanged and add a standard-library Python package backed by SQLite. Registries write both typed records and graph relations; agent/simulator behavior is injected through protocols so the core stays provider-neutral and physical lab execution stays human-gated.

**Tech Stack:** Python 3.13+, SQLite (`sqlite3`), dataclasses, argparse, pytest.

**Spec:** `docs/superpowers/specs/2026-08-19-researchos-design.md`

## Global Constraints

- Do not implement the orchestrator as a new entry under `skills/`.
- Do not require a new third-party runtime dependency for the core.
- Do not automatically accept/reject hypotheses or invent likelihood ratios.
- Do not automatically execute physical experiments.
- Persist provenance-bearing domain objects and graph relations.

---

### Task 1: Domain models and Bayesian updater

**Files:** `researchos/models.py`, `researchos/bayes.py`, `tests/_researchos/test_researchos.py`

**Interfaces:** immutable research dataclasses and `BayesianUpdater.update(prior_probability, likelihood_ratio) -> float`.

- [x] Write a failing test asserting a 0.5 prior updated by LR=3 gives posterior 0.75.
- [x] Run the focused test and confirm import/implementation failure.
- [x] Implement validated immutable models and odds-form Bayesian update.
- [x] Run the focused test and confirm pass.

### Task 2: Persistent store and research graph

**Files:** `researchos/store.py`, `tests/_researchos/test_researchos.py`

**Interfaces:** `ResearchStore` CRUD for goals, evidence, hypotheses, experiments, runs, critiques, measurements, nodes, edges, status/state updates, and audit snapshots.

- [x] Write a failing persistence test that closes/reopens the SQLite file.
- [x] Implement schema creation, relational persistence, graph-node mirroring, semantic edges, and event writes.
- [x] Re-run persistence tests and verify graph relations.

### Task 3: Registries and state machine

**Files:** `researchos/registries.py`, `researchos/state_machine.py`, `tests/_researchos/test_researchos.py`

**Interfaces:** `EvidenceLedger.add`, `HypothesisRegistry.add`, `ExperimentRegistry.add`, and `ResearchStateMachine.transition`.

- [x] Write tests for required graph links and a valid compute→critic→confidence→next path.
- [x] Add a failing invalid-transition assertion.
- [x] Implement registries and the explicit transition map.
- [x] Run tests to green.

### Task 4: Next-best-experiment decision engine

**Files:** `researchos/decision.py`, `tests/_researchos/test_researchos.py`

**Interfaces:** `DecisionEngine.rank(experiments, hypotheses) -> list[RankedExperiment]`.

- [x] Write a failing test where equal-feasibility experiments differ materially in expected information gain.
- [x] Implement weighted information gain, feasibility, budget-relative cost efficiency, hypothesis uncertainty, and risk penalty.
- [x] Confirm the more discriminating experiment ranks first.

### Task 5: Skill-aware agent and computational execution adapters

**Files:** `researchos/skills.py`, `researchos/agents.py`, `researchos/execution.py`, `tests/_researchos/test_researchos.py`

**Interfaces:** `SkillCatalog`, `AgentDispatcher`, `ScientificAgent`, and `ComputationalExecutor`.

- [x] Write failing tests using temporary `SKILL.md` fixtures and fake adapters.
- [x] Implement minimal frontmatter discovery and skill resolution.
- [x] Implement agent dispatch and computational executor protocol.
- [x] Verify run persistence and `awaiting_critique` status after successful execution.

### Task 6: Orchestrator, critic, measurement loop, snapshot, and CLI

**Files:** `researchos/orchestrator.py`, `researchos/cli.py`, `researchos/__init__.py`, `researchos/__main__.py`, `tests/_researchos/test_researchos.py`

**Interfaces:** `ResearchOrchestrator` facade and `python -m researchos` CLI.

- [x] Write end-to-end failing tests for graph creation, posterior update, critique persistence, CLI goal creation, and audit snapshot.
- [x] Implement the orchestrator using earlier components without duplicating their logic.
- [x] Add CLI commands for init, goal, evidence, hypothesis, experiment, next, critique, measure, state, and status.
- [x] Run the ResearchOS suite to green.

### Task 7: Documentation and CI

**Files:** `researchos/README.md`, `.github/workflows/researchos-tests.yml`

- [x] Document architecture, physical-lab boundary, adapter model, and quick-start commands.
- [x] Add path-scoped GitHub Actions coverage.
- [x] Run local compile and test verification before opening the PR.
