from __future__ import annotations

from enum import Enum


class ResearchState(str, Enum):
    GOAL_DEFINED = "goal_defined"
    EVIDENCE_GATHERING = "evidence_gathering"
    HYPOTHESIS_FORMATION = "hypothesis_formation"
    EXPERIMENT_PLANNING = "experiment_planning"
    COMPUTATIONAL_EXPERIMENT = "computational_experiment"
    CRITIQUE = "critique"
    PHYSICAL_EXPERIMENT = "physical_experiment"
    CONFIDENCE_UPDATE = "confidence_update"
    NEXT_EXPERIMENT = "next_experiment"
    COMPLETED = "completed"


class ResearchStateMachine:
    _allowed = {
        ResearchState.GOAL_DEFINED: {ResearchState.EVIDENCE_GATHERING},
        ResearchState.EVIDENCE_GATHERING: {ResearchState.HYPOTHESIS_FORMATION, ResearchState.COMPLETED},
        ResearchState.HYPOTHESIS_FORMATION: {ResearchState.EXPERIMENT_PLANNING, ResearchState.EVIDENCE_GATHERING},
        ResearchState.EXPERIMENT_PLANNING: {ResearchState.COMPUTATIONAL_EXPERIMENT, ResearchState.PHYSICAL_EXPERIMENT},
        ResearchState.COMPUTATIONAL_EXPERIMENT: {ResearchState.CRITIQUE},
        ResearchState.PHYSICAL_EXPERIMENT: {ResearchState.CRITIQUE},
        ResearchState.CRITIQUE: {ResearchState.CONFIDENCE_UPDATE, ResearchState.EXPERIMENT_PLANNING},
        ResearchState.CONFIDENCE_UPDATE: {ResearchState.NEXT_EXPERIMENT},
        ResearchState.NEXT_EXPERIMENT: {
            ResearchState.EXPERIMENT_PLANNING,
            ResearchState.EVIDENCE_GATHERING,
            ResearchState.PHYSICAL_EXPERIMENT,
            ResearchState.COMPLETED,
        },
        ResearchState.COMPLETED: set(),
    }

    def transition(self, current: ResearchState | str, target: ResearchState | str) -> ResearchState:
        current = ResearchState(current)
        target = ResearchState(target)
        if target not in self._allowed[current]:
            raise ValueError(f"invalid research-state transition: {current.value} -> {target.value}")
        return target
