from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from .models import Critique, EvidenceRecord, Experiment, ExperimentKind, ExperimentRun, Hypothesis, Measurement, ResearchGoal


class ResearchStore:
    """SQLite persistence for registries plus a lightweight property graph."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, question TEXT NOT NULL,
                success_criteria TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, claim TEXT NOT NULL, source TEXT NOT NULL,
                reliability REAL NOT NULL, direction TEXT NOT NULL, likelihood_ratio REAL,
                metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS hypotheses (
                id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, statement TEXT NOT NULL, mechanism TEXT NOT NULL,
                prior_probability REAL NOT NULL, posterior_probability REAL NOT NULL, status TEXT NOT NULL,
                metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL, title TEXT NOT NULL,
                kind TEXT NOT NULL, cost REAL NOT NULL, expected_information_gain REAL NOT NULL,
                feasibility REAL NOT NULL, risk REAL NOT NULL, status TEXT NOT NULL,
                skill_names_json TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS measurements (
                id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL,
                outcome TEXT NOT NULL, likelihood_ratio REAL NOT NULL, value REAL, unit TEXT,
                metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS critiques (
                id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, verdict TEXT NOT NULL,
                issues_json TEXT NOT NULL, confidence REAL NOT NULL, metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiment_runs (
                id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, executor TEXT NOT NULL,
                summary TEXT NOT NULL, artifacts_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY, node_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL, relation TEXT NOT NULL,
                target_id TEXT NOT NULL, weight REAL NOT NULL DEFAULT 1.0,
                metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_id, relation, target_id)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._conn.commit()

    def _node(self, entity_id: str, node_type: str, payload: dict[str, Any], created_at: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_nodes(id, node_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (entity_id, node_type, json.dumps(payload, sort_keys=True, default=str), created_at),
        )

    def _event(self, event_type: str, entity_type: str, entity_id: str, payload: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO events(event_type, entity_type, entity_id, payload_json) VALUES (?, ?, ?, ?)",
            (event_type, entity_type, entity_id, json.dumps(payload, sort_keys=True, default=str)),
        )

    def insert_goal(self, goal: ResearchGoal) -> ResearchGoal:
        with self._conn:
            self._conn.execute(
                "INSERT INTO goals VALUES (?, ?, ?, ?, ?, ?)",
                (goal.id, goal.title, goal.question, goal.success_criteria, goal.state, goal.created_at),
            )
            self._node(goal.id, "goal", asdict(goal), goal.created_at)
            self._event("created", "goal", goal.id, asdict(goal))
        return goal

    def get_goal(self, goal_id: str) -> ResearchGoal:
        row = self._require("SELECT * FROM goals WHERE id = ?", (goal_id,), "goal")
        return ResearchGoal(**dict(row))

    def update_goal_state(self, goal_id: str, state: str) -> ResearchGoal:
        goal = self.get_goal(goal_id)
        updated = replace(goal, state=state)
        with self._conn:
            self._conn.execute("UPDATE goals SET state = ? WHERE id = ?", (state, goal_id))
            self._node(goal_id, "goal", asdict(updated), updated.created_at)
            self._event("state_changed", "goal", goal_id, {"state": state})
        return updated

    def insert_evidence(self, evidence: EvidenceRecord) -> EvidenceRecord:
        with self._conn:
            self._conn.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (evidence.id, evidence.goal_id, evidence.claim, evidence.source, evidence.reliability,
                 evidence.direction, evidence.likelihood_ratio, json.dumps(evidence.metadata), evidence.created_at),
            )
            self._node(evidence.id, "evidence", asdict(evidence), evidence.created_at)
            self._event("created", "evidence", evidence.id, asdict(evidence))
        return evidence

    def get_evidence(self, evidence_id: str) -> EvidenceRecord:
        row = self._require("SELECT * FROM evidence WHERE id = ?", (evidence_id,), "evidence")
        data = dict(row)
        data["metadata"] = json.loads(data.pop("metadata_json"))
        return EvidenceRecord(**data)

    def list_evidence(self, goal_id: str) -> list[EvidenceRecord]:
        rows = self._conn.execute("SELECT id FROM evidence WHERE goal_id = ? ORDER BY created_at", (goal_id,)).fetchall()
        return [self.get_evidence(row["id"]) for row in rows]

    def insert_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        with self._conn:
            self._conn.execute(
                "INSERT INTO hypotheses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (hypothesis.id, hypothesis.goal_id, hypothesis.statement, hypothesis.mechanism,
                 hypothesis.prior_probability, hypothesis.posterior_probability, hypothesis.status,
                 json.dumps(hypothesis.metadata), hypothesis.created_at),
            )
            self._node(hypothesis.id, "hypothesis", asdict(hypothesis), hypothesis.created_at)
            self._event("created", "hypothesis", hypothesis.id, asdict(hypothesis))
        return hypothesis

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis:
        row = self._require("SELECT * FROM hypotheses WHERE id = ?", (hypothesis_id,), "hypothesis")
        data = dict(row)
        data["metadata"] = json.loads(data.pop("metadata_json"))
        return Hypothesis(**data)

    def list_hypotheses(self, goal_id: str) -> list[Hypothesis]:
        rows = self._conn.execute("SELECT id FROM hypotheses WHERE goal_id = ? ORDER BY created_at", (goal_id,)).fetchall()
        return [self.get_hypothesis(row["id"]) for row in rows]

    def update_hypothesis_posterior(self, hypothesis_id: str, posterior_probability: float) -> Hypothesis:
        hypothesis = self.get_hypothesis(hypothesis_id)
        updated = replace(hypothesis, posterior_probability=posterior_probability)
        with self._conn:
            self._conn.execute(
                "UPDATE hypotheses SET posterior_probability = ? WHERE id = ?",
                (posterior_probability, hypothesis_id),
            )
            self._node(hypothesis_id, "hypothesis", asdict(updated), updated.created_at)
            self._event("confidence_updated", "hypothesis", hypothesis_id, {"posterior_probability": posterior_probability})
        return updated

    def insert_experiment(self, experiment: Experiment) -> Experiment:
        with self._conn:
            self._conn.execute(
                "INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (experiment.id, experiment.goal_id, experiment.hypothesis_id, experiment.title,
                 experiment.kind.value, experiment.cost, experiment.expected_information_gain,
                 experiment.feasibility, experiment.risk, experiment.status,
                 json.dumps(experiment.skill_names), json.dumps(experiment.metadata), experiment.created_at),
            )
            payload = asdict(experiment)
            payload["kind"] = experiment.kind.value
            self._node(experiment.id, "experiment", payload, experiment.created_at)
            self._event("created", "experiment", experiment.id, payload)
        return experiment

    def get_experiment(self, experiment_id: str) -> Experiment:
        row = self._require("SELECT * FROM experiments WHERE id = ?", (experiment_id,), "experiment")
        data = dict(row)
        data["kind"] = ExperimentKind(data["kind"])
        data["skill_names"] = tuple(json.loads(data.pop("skill_names_json")))
        data["metadata"] = json.loads(data.pop("metadata_json"))
        return Experiment(**data)

    def list_experiments(self, goal_id: str, status: str | None = None) -> list[Experiment]:
        sql = "SELECT id FROM experiments WHERE goal_id = ?"
        params: tuple[Any, ...] = (goal_id,)
        if status is not None:
            sql += " AND status = ?"
            params += (status,)
        sql += " ORDER BY created_at"
        rows = self._conn.execute(sql, params).fetchall()
        return [self.get_experiment(row["id"]) for row in rows]

    def update_experiment_status(self, experiment_id: str, status: str) -> Experiment:
        experiment = self.get_experiment(experiment_id)
        updated = replace(experiment, status=status)
        with self._conn:
            self._conn.execute("UPDATE experiments SET status = ? WHERE id = ?", (status, experiment_id))
            payload = asdict(updated)
            payload["kind"] = updated.kind.value
            self._node(experiment_id, "experiment", payload, updated.created_at)
            self._event("status_changed", "experiment", experiment_id, {"status": status})
        return updated

    def insert_measurement(self, measurement: Measurement) -> Measurement:
        with self._conn:
            self._conn.execute(
                "INSERT INTO measurements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (measurement.id, measurement.experiment_id, measurement.hypothesis_id, measurement.outcome,
                 measurement.likelihood_ratio, measurement.value, measurement.unit,
                 json.dumps(measurement.metadata), measurement.created_at),
            )
            self._node(measurement.id, "measurement", asdict(measurement), measurement.created_at)
            self._event("created", "measurement", measurement.id, asdict(measurement))
        return measurement

    def insert_experiment_run(self, run: ExperimentRun) -> ExperimentRun:
        with self._conn:
            self._conn.execute(
                "INSERT INTO experiment_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run.id, run.experiment_id, run.executor, run.summary, json.dumps(run.artifacts),
                 json.dumps(run.metadata), run.created_at),
            )
            self._node(run.id, "experiment_run", asdict(run), run.created_at)
            self._event("created", "experiment_run", run.id, asdict(run))
        return run

    def get_experiment_run(self, run_id: str) -> ExperimentRun:
        row = self._require("SELECT * FROM experiment_runs WHERE id = ?", (run_id,), "experiment run")
        data = dict(row)
        data["artifacts"] = tuple(json.loads(data.pop("artifacts_json")))
        data["metadata"] = json.loads(data.pop("metadata_json"))
        return ExperimentRun(**data)

    def insert_critique(self, critique: Critique) -> Critique:
        with self._conn:
            self._conn.execute(
                "INSERT INTO critiques VALUES (?, ?, ?, ?, ?, ?, ?)",
                (critique.id, critique.experiment_id, critique.verdict, json.dumps(critique.issues),
                 critique.confidence, json.dumps(critique.metadata), critique.created_at),
            )
            self._node(critique.id, "critique", asdict(critique), critique.created_at)
            self._event("created", "critique", critique.id, asdict(critique))
        return critique

    def get_critique(self, critique_id: str) -> Critique:
        row = self._require("SELECT * FROM critiques WHERE id = ?", (critique_id,), "critique")
        data = dict(row)
        data["issues"] = tuple(json.loads(data.pop("issues_json")))
        data["metadata"] = json.loads(data.pop("metadata_json"))
        return Critique(**data)

    def list_critiques(self, goal_id: str) -> list[Critique]:
        rows = self._conn.execute(
            """SELECT c.id FROM critiques c
               JOIN experiments e ON e.id = c.experiment_id
               WHERE e.goal_id = ? ORDER BY c.created_at""",
            (goal_id,),
        ).fetchall()
        return [self.get_critique(row["id"]) for row in rows]

    def list_measurements(self, goal_id: str) -> list[Measurement]:
        rows = self._conn.execute(
            """SELECT m.id FROM measurements m
               JOIN experiments e ON e.id = m.experiment_id
               WHERE e.goal_id = ? ORDER BY m.created_at""",
            (goal_id,),
        ).fetchall()
        result: list[Measurement] = []
        for row in rows:
            data = dict(self._require("SELECT * FROM measurements WHERE id = ?", (row["id"],), "measurement"))
            data["metadata"] = json.loads(data.pop("metadata_json"))
            result.append(Measurement(**data))
        return result

    def list_nodes(self, node_type: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT id, node_type, payload_json, created_at FROM graph_nodes"
        params: tuple[Any, ...] = ()
        if node_type is not None:
            sql += " WHERE node_type = ?"
            params = (node_type,)
        sql += " ORDER BY created_at, id"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": row["id"],
                "node_type": row["node_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def add_edge(
        self,
        source_id: str,
        relation: str,
        target_id: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO graph_edges(source_id, relation, target_id, weight, metadata_json) VALUES (?, ?, ?, ?, ?)",
                (source_id, relation, target_id, weight, json.dumps(metadata or {}, sort_keys=True)),
            )

    def list_edges(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT source_id, relation, target_id, weight, metadata_json, created_at FROM graph_edges ORDER BY id"
        ).fetchall()
        return [
            {
                "source_id": row["source_id"],
                "relation": row["relation"],
                "target_id": row["target_id"],
                "weight": row["weight"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _require(self, sql: str, params: tuple[Any, ...], entity: str) -> sqlite3.Row:
        row = self._conn.execute(sql, params).fetchone()
        if row is None:
            raise KeyError(f"unknown {entity}: {params[0]}")
        return row
