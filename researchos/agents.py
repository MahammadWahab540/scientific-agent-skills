from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence
from uuid import uuid4

from .skills import SkillCatalog, SkillDescriptor


@dataclass(frozen=True, slots=True)
class AgentTask:
    id: str
    goal_id: str
    objective: str
    skill_names: tuple[str, ...] = ()
    inputs: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        goal_id: str,
        objective: str,
        skill_names: tuple[str, ...] = (),
        inputs: dict[str, Any] | None = None,
    ) -> "AgentTask":
        return cls(f"task_{uuid4().hex}", goal_id, objective.strip(), tuple(skill_names), inputs or {})


@dataclass(frozen=True, slots=True)
class AgentResult:
    summary: str
    outputs: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[str, ...] = ()


class ScientificAgent(Protocol):
    name: str

    def run(self, task: AgentTask, skills: Sequence[SkillDescriptor]) -> AgentResult: ...


class AgentDispatcher:
    """Resolve declared Agent Skills, then dispatch a bounded task to an agent adapter."""

    def __init__(self, skill_catalog: SkillCatalog) -> None:
        self.skill_catalog = skill_catalog

    def dispatch(self, agent: ScientificAgent, task: AgentTask) -> AgentResult:
        skills = tuple(self.skill_catalog.get(name) for name in task.skill_names)
        return agent.run(task, skills)
