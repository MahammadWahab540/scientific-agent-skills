from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from .models import Experiment
from .skills import SkillDescriptor


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    summary: str
    artifacts: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ComputationalExecutor(Protocol):
    name: str

    def execute(
        self,
        experiment: Experiment,
        skills: Sequence[SkillDescriptor],
    ) -> ExecutionResult: ...
