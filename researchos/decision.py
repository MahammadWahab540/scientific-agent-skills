from __future__ import annotations

from dataclasses import dataclass

from .models import Experiment, Hypothesis


@dataclass(frozen=True, slots=True)
class RankedExperiment:
    experiment: Experiment
    score: float
    components: dict[str, float]


class DecisionEngine:
    """Rank experiments, never hypotheses, using information value and constraints."""

    def __init__(
        self,
        budget: float,
        information_weight: float = 0.45,
        feasibility_weight: float = 0.25,
        cost_weight: float = 0.10,
        uncertainty_weight: float = 0.20,
        risk_penalty: float = 0.20,
    ) -> None:
        if budget <= 0:
            raise ValueError("budget must be greater than 0")
        self.budget = budget
        self.information_weight = information_weight
        self.feasibility_weight = feasibility_weight
        self.cost_weight = cost_weight
        self.uncertainty_weight = uncertainty_weight
        self.risk_penalty = risk_penalty

    def score(self, experiment: Experiment, hypothesis: Hypothesis) -> RankedExperiment:
        if experiment.cost > self.budget:
            return RankedExperiment(experiment, float("-inf"), {"over_budget": 1.0})
        cost_efficiency = max(0.0, 1.0 - (experiment.cost / self.budget))
        uncertainty = 1.0 - abs(hypothesis.posterior_probability - 0.5) * 2.0
        components = {
            "information_gain": experiment.expected_information_gain,
            "feasibility": experiment.feasibility,
            "cost_efficiency": cost_efficiency,
            "hypothesis_uncertainty": uncertainty,
            "risk": experiment.risk,
        }
        score = (
            self.information_weight * components["information_gain"]
            + self.feasibility_weight * components["feasibility"]
            + self.cost_weight * components["cost_efficiency"]
            + self.uncertainty_weight * components["hypothesis_uncertainty"]
            - self.risk_penalty * components["risk"]
        )
        return RankedExperiment(experiment, score, components)

    def rank(
        self,
        experiments: list[Experiment],
        hypotheses: dict[str, Hypothesis],
    ) -> list[RankedExperiment]:
        ranked = [
            self.score(experiment, hypotheses[experiment.hypothesis_id])
            for experiment in experiments
            if experiment.status == "planned" and experiment.hypothesis_id in hypotheses
        ]
        return sorted(ranked, key=lambda item: item.score, reverse=True)
