from __future__ import annotations

from typing import Any

from .bayes import BayesianUpdater
from .decision import DecisionEngine, RankedExperiment
from .execution import ComputationalExecutor
from .models import Critique, Experiment, ExperimentKind, ExperimentRun, Hypothesis, Measurement, ResearchGoal
from .registries import EvidenceLedger, ExperimentRegistry, HypothesisRegistry
from .skills import SkillCatalog
from .state_machine import ResearchState, ResearchStateMachine
from .store import ResearchStore


class ResearchOrchestrator:
    """Coordinate the research loop while keeping scientific execution pluggable."""

    def __init__(self, store: ResearchStore, skill_catalog: SkillCatalog | None = None) -> None:
        self.store = store
        self.skill_catalog = skill_catalog or SkillCatalog.discover()
        self.evidence = EvidenceLedger(store)
        self.hypotheses = HypothesisRegistry(store)
        self.experiments = ExperimentRegistry(store)
        self.bayes = BayesianUpdater()
        self.states = ResearchStateMachine()

    def create_goal(self, title: str, question: str, success_criteria: str) -> ResearchGoal:
        goal = ResearchGoal.create(title, question, success_criteria)
        return self.store.insert_goal(goal)

    def advance_goal(self, goal_id: str, target: ResearchState | str) -> ResearchGoal:
        goal = self.store.get_goal(goal_id)
        target_state = self.states.transition(goal.state, target)
        return self.store.update_goal_state(goal_id, target_state.value)

    def record_evidence(self, **kwargs: Any):
        return self.evidence.add(**kwargs)

    def register_hypothesis(self, **kwargs: Any) -> Hypothesis:
        return self.hypotheses.add(**kwargs)

    def plan_experiment(self, **kwargs: Any) -> Experiment:
        return self.experiments.add(**kwargs)

    def snapshot(self, goal_id: str) -> dict[str, Any]:
        self.store.get_goal(goal_id)
        return {
            "goal": self.store.get_goal(goal_id),
            "evidence": self.store.list_evidence(goal_id),
            "hypotheses": self.store.list_hypotheses(goal_id),
            "experiments": self.store.list_experiments(goal_id),
            "critiques": self.store.list_critiques(goal_id),
            "measurements": self.store.list_measurements(goal_id),
            "edges": self.store.list_edges(),
        }

    def next_best_experiment(self, goal_id: str, budget: float) -> RankedExperiment:
        experiments = self.store.list_experiments(goal_id, status="planned")
        if not experiments:
            raise LookupError(f"no planned experiments for goal {goal_id}")
        hypotheses = {h.id: h for h in self.store.list_hypotheses(goal_id)}
        ranked = DecisionEngine(budget=budget).rank(experiments, hypotheses)
        if not ranked or ranked[0].score == float("-inf"):
            raise LookupError("no planned experiment fits the decision constraints")
        return ranked[0]

    def execute_computational(
        self,
        experiment_id: str,
        executor: ComputationalExecutor,
    ) -> ExperimentRun:
        experiment = self.store.get_experiment(experiment_id)
        if experiment.kind is not ExperimentKind.COMPUTATIONAL:
            raise ValueError("physical experiments must be executed outside ResearchOS and ingested as measurements")
        skills = tuple(self.skill_catalog.get(name) for name in experiment.skill_names)
        self.store.update_experiment_status(experiment.id, "running")
        try:
            result = executor.execute(experiment, skills)
        except Exception:
            self.store.update_experiment_status(experiment.id, "failed")
            raise
        run = ExperimentRun.create(
            experiment_id=experiment.id,
            executor=executor.name,
            summary=result.summary,
            artifacts=result.artifacts,
            metadata=result.metadata,
        )
        self.store.insert_experiment_run(run)
        self.store.add_edge(experiment.id, "HAS_RUN", run.id)
        self.store.update_experiment_status(experiment.id, "awaiting_critique")
        return run

    def record_critique(
        self,
        experiment_id: str,
        verdict: str,
        issues: tuple[str, ...] = (),
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Critique:
        self.store.get_experiment(experiment_id)
        critique = Critique.create(experiment_id, verdict, issues, confidence, metadata)
        self.store.insert_critique(critique)
        self.store.add_edge(experiment_id, "REVIEWED_BY", critique.id, weight=confidence)
        return critique

    def record_measurement(
        self,
        experiment_id: str,
        outcome: str,
        likelihood_ratio: float,
        value: float | None = None,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Hypothesis:
        experiment = self.store.get_experiment(experiment_id)
        hypothesis = self.store.get_hypothesis(experiment.hypothesis_id)
        measurement = Measurement.create(
            experiment_id=experiment.id,
            hypothesis_id=hypothesis.id,
            outcome=outcome,
            likelihood_ratio=likelihood_ratio,
            value=value,
            unit=unit,
            metadata=metadata,
        )
        self.store.insert_measurement(measurement)
        self.store.add_edge(experiment.id, "PRODUCED_MEASUREMENT", measurement.id)
        self.store.add_edge(measurement.id, "UPDATES", hypothesis.id)
        posterior = self.bayes.update(hypothesis.posterior_probability, likelihood_ratio)
        updated = self.store.update_hypothesis_posterior(hypothesis.id, posterior)
        self.store.update_experiment_status(experiment.id, "completed")
        return updated
