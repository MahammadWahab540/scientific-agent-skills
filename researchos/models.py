from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExperimentKind(str, Enum):
    COMPUTATIONAL = "computational"
    PHYSICAL = "physical"


@dataclass(frozen=True, slots=True)
class ResearchGoal:
    id: str
    title: str
    question: str
    success_criteria: str
    state: str = "goal_defined"
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(cls, title: str, question: str, success_criteria: str) -> "ResearchGoal":
        return cls(_id("goal"), title.strip(), question.strip(), success_criteria.strip())


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: str
    goal_id: str
    claim: str
    source: str
    reliability: float
    direction: str
    likelihood_ratio: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        goal_id: str,
        claim: str,
        source: str,
        reliability: float,
        direction: str,
        likelihood_ratio: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "EvidenceRecord":
        if not 0 <= reliability <= 1:
            raise ValueError("reliability must be between 0 and 1")
        if likelihood_ratio is not None and likelihood_ratio <= 0:
            raise ValueError("likelihood_ratio must be greater than 0")
        return cls(
            _id("ev"), goal_id, claim.strip(), source.strip(), reliability,
            direction.strip().lower(), likelihood_ratio, metadata or {},
        )


@dataclass(frozen=True, slots=True)
class Hypothesis:
    id: str
    goal_id: str
    statement: str
    mechanism: str = ""
    prior_probability: float = 0.5
    posterior_probability: float = 0.5
    status: str = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        goal_id: str,
        statement: str,
        mechanism: str = "",
        prior_probability: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> "Hypothesis":
        if not 0 < prior_probability < 1:
            raise ValueError("prior_probability must be between 0 and 1, exclusive")
        return cls(
            _id("hyp"), goal_id, statement.strip(), mechanism.strip(),
            prior_probability, prior_probability, "candidate", metadata or {},
        )


@dataclass(frozen=True, slots=True)
class Experiment:
    id: str
    goal_id: str
    hypothesis_id: str
    title: str
    kind: ExperimentKind
    cost: float
    expected_information_gain: float
    feasibility: float
    risk: float
    status: str = "planned"
    skill_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(
        cls,
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
    ) -> "Experiment":
        kind = ExperimentKind(kind)
        if cost < 0:
            raise ValueError("cost cannot be negative")
        for field_name, value in (
            ("expected_information_gain", expected_information_gain),
            ("feasibility", feasibility),
            ("risk", risk),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")
        return cls(
            _id("exp"), goal_id, hypothesis_id, title.strip(), kind, cost,
            expected_information_gain, feasibility, risk, "planned",
            tuple(skill_names), metadata or {},
        )


@dataclass(frozen=True, slots=True)
class Measurement:
    id: str
    experiment_id: str
    hypothesis_id: str
    outcome: str
    likelihood_ratio: float
    value: float | None = None
    unit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        experiment_id: str,
        hypothesis_id: str,
        outcome: str,
        likelihood_ratio: float,
        value: float | None = None,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Measurement":
        if likelihood_ratio <= 0:
            raise ValueError("likelihood_ratio must be greater than 0")
        return cls(
            _id("meas"), experiment_id, hypothesis_id, outcome.strip(),
            likelihood_ratio, value, unit, metadata or {},
        )


@dataclass(frozen=True, slots=True)
class Critique:
    id: str
    experiment_id: str
    verdict: str
    issues: tuple[str, ...]
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        experiment_id: str,
        verdict: str,
        issues: tuple[str, ...] = (),
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> "Critique":
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return cls(_id("crit"), experiment_id, verdict.strip(), tuple(issues), confidence, metadata or {})


@dataclass(frozen=True, slots=True)
class ExperimentRun:
    id: str
    experiment_id: str
    executor: str
    summary: str
    artifacts: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        experiment_id: str,
        executor: str,
        summary: str,
        artifacts: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "ExperimentRun":
        return cls(_id("run"), experiment_id, executor.strip(), summary.strip(), tuple(artifacts), metadata or {})
