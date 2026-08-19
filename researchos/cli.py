from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from .models import ExperimentKind
from .orchestrator import ResearchOrchestrator
from .state_machine import ResearchState
from .store import ResearchStore


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _print(value: Any) -> None:
    print(json.dumps(_jsonable(value), indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researchos", description="Operate the persistent ResearchOS loop")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize the SQLite research store")
    init.add_argument("--db", default=".researchos/research.db")

    goal = sub.add_parser("goal", help="Create a research goal")
    _db(goal)
    goal.add_argument("--title", required=True)
    goal.add_argument("--question", required=True)
    goal.add_argument("--success", required=True)

    evidence = sub.add_parser("evidence", help="Append evidence to the ledger")
    _db(evidence)
    evidence.add_argument("--goal", required=True)
    evidence.add_argument("--claim", required=True)
    evidence.add_argument("--source", required=True)
    evidence.add_argument("--reliability", type=float, required=True)
    evidence.add_argument("--direction", choices=("supporting", "challenging", "contextual"), default="contextual")
    evidence.add_argument("--likelihood-ratio", type=float)

    hypothesis = sub.add_parser("hypothesis", help="Register a candidate hypothesis")
    _db(hypothesis)
    hypothesis.add_argument("--goal", required=True)
    hypothesis.add_argument("--statement", required=True)
    hypothesis.add_argument("--mechanism", default="")
    hypothesis.add_argument("--prior", type=float, default=0.5)
    hypothesis.add_argument("--evidence", action="append", default=[])

    experiment = sub.add_parser("experiment", help="Plan a computational or physical experiment")
    _db(experiment)
    experiment.add_argument("--goal", required=True)
    experiment.add_argument("--hypothesis", required=True)
    experiment.add_argument("--title", required=True)
    experiment.add_argument("--kind", choices=[kind.value for kind in ExperimentKind], required=True)
    experiment.add_argument("--cost", type=float, required=True)
    experiment.add_argument("--information-gain", type=float, required=True)
    experiment.add_argument("--feasibility", type=float, required=True)
    experiment.add_argument("--risk", type=float, default=0.0)
    experiment.add_argument("--skill", action="append", default=[])

    next_parser = sub.add_parser("next", help="Rank and return the next-best planned experiment")
    _db(next_parser)
    next_parser.add_argument("--goal", required=True)
    next_parser.add_argument("--budget", type=float, required=True)

    critique = sub.add_parser("critique", help="Persist an independent critique")
    _db(critique)
    critique.add_argument("--experiment", required=True)
    critique.add_argument("--verdict", required=True)
    critique.add_argument("--issue", action="append", default=[])
    critique.add_argument("--confidence", type=float, default=0.5)

    measure = sub.add_parser("measure", help="Record measured evidence and update hypothesis confidence")
    _db(measure)
    measure.add_argument("--experiment", required=True)
    measure.add_argument("--outcome", required=True)
    measure.add_argument("--likelihood-ratio", type=float, required=True)
    measure.add_argument("--value", type=float)
    measure.add_argument("--unit")

    state = sub.add_parser("state", help="Advance the explicit research state machine")
    _db(state)
    state.add_argument("--goal", required=True)
    state.add_argument("--to", choices=[item.value for item in ResearchState], required=True)

    status = sub.add_parser("status", help="Show goal, hypotheses, experiments, and knowledge-graph edges")
    _db(status)
    status.add_argument("--goal", required=True)
    return parser


def _db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", default=".researchos/research.db")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ResearchStore(args.db)
    os = ResearchOrchestrator(store)
    try:
        if args.command == "init":
            _print({"db": str(store.path), "initialized": True})
        elif args.command == "goal":
            _print(os.create_goal(args.title, args.question, args.success))
        elif args.command == "evidence":
            _print(os.record_evidence(
                goal_id=args.goal,
                claim=args.claim,
                source=args.source,
                reliability=args.reliability,
                direction=args.direction,
                likelihood_ratio=args.likelihood_ratio,
            ))
        elif args.command == "hypothesis":
            _print(os.register_hypothesis(
                goal_id=args.goal,
                statement=args.statement,
                mechanism=args.mechanism,
                prior_probability=args.prior,
                evidence_ids=args.evidence,
            ))
        elif args.command == "experiment":
            _print(os.plan_experiment(
                goal_id=args.goal,
                hypothesis_id=args.hypothesis,
                title=args.title,
                kind=args.kind,
                cost=args.cost,
                expected_information_gain=args.information_gain,
                feasibility=args.feasibility,
                risk=args.risk,
                skill_names=tuple(args.skill),
            ))
        elif args.command == "next":
            _print(os.next_best_experiment(args.goal, args.budget))
        elif args.command == "critique":
            _print(os.record_critique(
                experiment_id=args.experiment,
                verdict=args.verdict,
                issues=tuple(args.issue),
                confidence=args.confidence,
            ))
        elif args.command == "measure":
            _print(os.record_measurement(
                experiment_id=args.experiment,
                outcome=args.outcome,
                likelihood_ratio=args.likelihood_ratio,
                value=args.value,
                unit=args.unit,
            ))
        elif args.command == "state":
            _print(os.advance_goal(args.goal, args.to))
        elif args.command == "status":
            _print(os.snapshot(args.goal))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
