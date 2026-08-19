from __future__ import annotations

from typing import Any

from .models import EvidenceRecord, Experiment, ExperimentKind, Hypothesis
from .store import ResearchStore


class EvidenceLedger:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store

    def add(
        self,
        goal_id: str,
        claim: str,
        source: str,
        reliability: float,
        direction: str,
        likelihood_ratio: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        self.store.get_goal(goal_id)
        evidence = EvidenceRecord.create(
            goal_id, claim, source, reliability, direction, likelihood_ratio, metadata
        )
        self.store.insert_evidence(evidence)
        self.store.add_edge(goal_id, "HAS_EVIDENCE", evidence.id, weight=reliability)
        return evidence


class HypothesisRegistry:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store

    def add(
        self,
        goal_id: str,
        statement: str,
        mechanism: str = "",
        prior_probability: float = 0.5,
        evidence_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Hypothesis:
        self.store.get_goal(goal_id)
        hypothesis = Hypothesis.create(goal_id, statement, mechanism, prior_probability, metadata)
        self.store.insert_hypothesis(hypothesis)
        self.store.add_edge(goal_id, "HAS_HYPOTHESIS", hypothesis.id)
        for evidence_id in evidence_ids or []:
            evidence = self.store.get_evidence(evidence_id)
            relation = {
                "supporting": "SUPPORTED_BY",
                "challenging": "CHALLENGED_BY",
            }.get(evidence.direction, "INFORMED_BY")
            self.store.add_edge(hypothesis.id, relation, evidence.id, weight=evidence.reliability)
        return hypothesis


class ExperimentRegistry:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store

    def add(
        self,
        goal_id: str,
        hypothesis_id: str,
        title: str,
        kind: ExperimentKind | str,
        cost: float,
        expected_information_gain: float,
        feasibility: float,
        risk: float,
        skill_names: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Experiment:
        self.store.get_goal(goal_id)
        hypothesis = self.store.get_hypothesis(hypothesis_id)
        if hypothesis.goal_id != goal_id:
            raise ValueError("experiment hypothesis must belong to the same research goal")
        experiment = Experiment.create(
            goal_id, hypothesis_id, title, kind, cost, expected_information_gain,
            feasibility, risk, skill_names, metadata,
        )
        self.store.insert_experiment(experiment)
        self.store.add_edge(goal_id, "HAS_EXPERIMENT", experiment.id)
        self.store.add_edge(hypothesis_id, "TESTED_BY", experiment.id)
        for skill_name in experiment.skill_names:
            self.store.add_edge(experiment.id, "USES_SKILL", f"skill:{skill_name}")
        return experiment
