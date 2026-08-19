from pathlib import Path

import pytest

from researchos.bayes import BayesianUpdater
from researchos.decision import DecisionEngine
from researchos.models import Experiment, ExperimentKind, Hypothesis
from researchos.orchestrator import ResearchOrchestrator
from researchos.skills import SkillCatalog
from researchos.state_machine import ResearchState, ResearchStateMachine
from researchos.store import ResearchStore


def test_bayesian_update_uses_likelihood_ratio():
    updater = BayesianUpdater()
    posterior = updater.update(0.50, 3.0)
    assert posterior == pytest.approx(0.75)
    assert updater.update(0.50, 1 / 3) == pytest.approx(0.25)


def test_decision_engine_prefers_information_gain_when_feasibility_is_equal():
    hypothesis = Hypothesis.create("goal-1", "Coating A reduces heat gain", prior_probability=0.5)
    low_info = Experiment.create(
        goal_id="goal-1",
        hypothesis_id=hypothesis.id,
        title="Cheap weak simulation",
        kind=ExperimentKind.COMPUTATIONAL,
        cost=100,
        expected_information_gain=0.20,
        feasibility=0.90,
        risk=0.05,
    )
    high_info = Experiment.create(
        goal_id="goal-1",
        hypothesis_id=hypothesis.id,
        title="Discriminating optical simulation",
        kind=ExperimentKind.COMPUTATIONAL,
        cost=300,
        expected_information_gain=0.85,
        feasibility=0.90,
        risk=0.05,
    )
    engine = DecisionEngine(budget=1000)
    ranked = engine.rank([low_info, high_info], {hypothesis.id: hypothesis})
    assert ranked[0].experiment.id == high_info.id
    assert ranked[0].score > ranked[1].score


def test_state_machine_supports_compute_critic_update_loop_and_rejects_invalid_transition():
    machine = ResearchStateMachine()
    assert machine.transition(ResearchState.GOAL_DEFINED, ResearchState.EVIDENCE_GATHERING) == ResearchState.EVIDENCE_GATHERING
    assert machine.transition(ResearchState.COMPUTATIONAL_EXPERIMENT, ResearchState.CRITIQUE) == ResearchState.CRITIQUE
    assert machine.transition(ResearchState.CRITIQUE, ResearchState.CONFIDENCE_UPDATE) == ResearchState.CONFIDENCE_UPDATE
    assert machine.transition(ResearchState.CONFIDENCE_UPDATE, ResearchState.NEXT_EXPERIMENT) == ResearchState.NEXT_EXPERIMENT
    with pytest.raises(ValueError, match="invalid research-state transition"):
        machine.transition(ResearchState.GOAL_DEFINED, ResearchState.PHYSICAL_EXPERIMENT)


def test_skill_catalog_discovers_local_agent_skills(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "hypothesis-generation"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: hypothesis-generation\n"
        "description: Formulate testable evidence-bounded hypotheses and rival explanations.\n"
        "allowed-tools: Read Write Bash\n"
        "---\n\n# Hypothesis Generation\n",
        encoding="utf-8",
    )
    catalog = SkillCatalog.discover(tmp_path / "skills")
    assert catalog.get("hypothesis-generation").name == "hypothesis-generation"
    assert catalog.search("rival explanations")[0].name == "hypothesis-generation"


def test_orchestrator_persists_research_graph_and_updates_hypothesis_confidence(tmp_path: Path):
    db_path = tmp_path / "research.db"
    store = ResearchStore(db_path)
    os = ResearchOrchestrator(store)

    goal = os.create_goal(
        title="Passive cooling coating",
        question="Can the coating reduce internal storage temperature?",
        success_criteria="At least 3 C reduction under defined outdoor conditions",
    )
    evidence = os.record_evidence(
        goal_id=goal.id,
        claim="High solar reflectance is associated with lower daytime heat gain.",
        source="paper:example-doi",
        reliability=0.8,
        direction="supporting",
    )
    hypothesis = os.register_hypothesis(
        goal_id=goal.id,
        statement="A high-reflectance coating reduces daytime heat gain.",
        mechanism="Reduced absorbed solar flux lowers envelope heat input.",
        prior_probability=0.5,
        evidence_ids=[evidence.id],
    )
    experiment = os.plan_experiment(
        goal_id=goal.id,
        hypothesis_id=hypothesis.id,
        title="Coupled optical-thermal simulation",
        kind=ExperimentKind.COMPUTATIONAL,
        cost=250,
        expected_information_gain=0.8,
        feasibility=0.95,
        risk=0.05,
        skill_names=("hypothesis-generation",),
    )

    ranked = os.next_best_experiment(goal.id, budget=1000)
    assert ranked.experiment.id == experiment.id

    updated = os.record_measurement(
        experiment_id=experiment.id,
        outcome="Simulation supports lower heat gain under the preregistered boundary conditions.",
        likelihood_ratio=4.0,
        value=3.4,
        unit="degC",
    )
    assert updated.posterior_probability == pytest.approx(0.8)

    edges = store.list_edges()
    relations = {(edge["source_id"], edge["relation"], edge["target_id"]) for edge in edges}
    assert (goal.id, "HAS_EVIDENCE", evidence.id) in relations
    assert (goal.id, "HAS_HYPOTHESIS", hypothesis.id) in relations
    assert (hypothesis.id, "TESTED_BY", experiment.id) in relations
    assert any(relation == "PRODUCED_MEASUREMENT" for _, relation, _ in relations)

    reopened = ResearchStore(db_path)
    assert reopened.get_goal(goal.id).title == "Passive cooling coating"
    assert reopened.get_hypothesis(hypothesis.id).posterior_probability == pytest.approx(0.8)


def test_independent_critique_is_persisted_and_linked_to_experiment(tmp_path: Path):
    store = ResearchStore(tmp_path / "critique.db")
    os = ResearchOrchestrator(store)
    goal = os.create_goal("Cooling", "Does it cool?", "3 C reduction")
    hypothesis = os.register_hypothesis(goal_id=goal.id, statement="It cools", prior_probability=0.5)
    experiment = os.plan_experiment(
        goal_id=goal.id,
        hypothesis_id=hypothesis.id,
        title="Simulation",
        kind=ExperimentKind.COMPUTATIONAL,
        cost=10,
        expected_information_gain=0.7,
        feasibility=1.0,
        risk=0.0,
    )
    critique = os.record_critique(
        experiment_id=experiment.id,
        verdict="proceed_with_caution",
        issues=("humidity sensitivity not yet tested",),
        confidence=0.8,
    )
    assert store.get_critique(critique.id).verdict == "proceed_with_caution"
    assert any(
        edge["source_id"] == experiment.id
        and edge["relation"] == "REVIEWED_BY"
        and edge["target_id"] == critique.id
        for edge in store.list_edges()
    )


def test_computational_executor_is_dispatched_and_run_is_persisted(tmp_path: Path):
    from researchos.execution import ExecutionResult

    class FakeExecutor:
        name = "fake-simulator"

        def execute(self, experiment, skills):
            assert experiment.kind == ExperimentKind.COMPUTATIONAL
            return ExecutionResult(
                summary="simulation completed",
                artifacts=("artifact://temperature-profile.json",),
                metadata={"solver": "fake"},
            )

    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "hypothesis-generation"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hypothesis-generation\ndescription: Generate testable hypotheses.\n---\n",
        encoding="utf-8",
    )
    store = ResearchStore(tmp_path / "runs.db")
    os = ResearchOrchestrator(store, skill_catalog=SkillCatalog.discover(skills_root))
    goal = os.create_goal("Cooling", "Does it cool?", "3 C reduction")
    hypothesis = os.register_hypothesis(goal_id=goal.id, statement="It cools", prior_probability=0.5)
    experiment = os.plan_experiment(
        goal_id=goal.id,
        hypothesis_id=hypothesis.id,
        title="Simulation",
        kind=ExperimentKind.COMPUTATIONAL,
        cost=10,
        expected_information_gain=0.7,
        feasibility=1.0,
        risk=0.0,
        skill_names=("hypothesis-generation",),
    )
    run = os.execute_computational(experiment.id, FakeExecutor())
    assert run.executor == "fake-simulator"
    assert store.get_experiment_run(run.id).summary == "simulation completed"
    assert store.get_experiment(experiment.id).status == "awaiting_critique"


def test_cli_can_initialize_and_create_goal(tmp_path: Path, capsys):
    import json
    from researchos.cli import main

    db = tmp_path / "cli.db"
    assert main(["init", "--db", str(db)]) == 0
    capsys.readouterr()
    assert main([
        "goal", "--db", str(db),
        "--title", "Cooling coating",
        "--question", "Can it cool?",
        "--success", "3 C reduction",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["title"] == "Cooling coating"
    assert payload["id"].startswith("goal_")


def test_agent_dispatcher_resolves_k_dense_skills_before_running_agent(tmp_path: Path):
    from researchos.agents import AgentDispatcher, AgentResult, AgentTask

    class FakeAgent:
        name = "hypothesis-agent"

        def run(self, task, skills):
            assert task.objective == "Generate rival hypotheses"
            assert [skill.name for skill in skills] == ["hypothesis-generation"]
            return AgentResult(summary="generated 3 candidate rivals", outputs={"count": 3})

    skill_dir = tmp_path / "skills" / "hypothesis-generation"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hypothesis-generation\ndescription: Generate testable hypotheses.\n---\n",
        encoding="utf-8",
    )
    dispatcher = AgentDispatcher(SkillCatalog.discover(tmp_path / "skills"))
    result = dispatcher.dispatch(
        FakeAgent(),
        AgentTask.create("goal-1", "Generate rival hypotheses", ("hypothesis-generation",)),
    )
    assert result.outputs["count"] == 3


def test_goal_snapshot_returns_audit_ready_research_state(tmp_path: Path):
    store = ResearchStore(tmp_path / "snapshot.db")
    os = ResearchOrchestrator(store)
    goal = os.create_goal("Cooling", "Does it cool?", "3 C reduction")
    evidence = os.record_evidence(
        goal_id=goal.id,
        claim="Reflectance reduces absorbed flux",
        source="doi:test",
        reliability=0.7,
        direction="supporting",
    )
    hypothesis = os.register_hypothesis(
        goal_id=goal.id,
        statement="It cools",
        prior_probability=0.5,
        evidence_ids=[evidence.id],
    )
    experiment = os.plan_experiment(
        goal_id=goal.id,
        hypothesis_id=hypothesis.id,
        title="Simulation",
        kind=ExperimentKind.COMPUTATIONAL,
        cost=10,
        expected_information_gain=0.7,
        feasibility=1.0,
        risk=0.0,
    )
    os.record_critique(experiment.id, "reviewed", confidence=0.8)
    os.record_measurement(experiment.id, "supports prediction", 2.0)
    snapshot = os.snapshot(goal.id)
    assert snapshot["goal"].id == goal.id
    assert [item.id for item in snapshot["evidence"]] == [evidence.id]
    assert [item.id for item in snapshot["hypotheses"]] == [hypothesis.id]
    assert [item.id for item in snapshot["experiments"]] == [experiment.id]
    assert len(snapshot["critiques"]) == 1
    assert len(snapshot["measurements"]) == 1
