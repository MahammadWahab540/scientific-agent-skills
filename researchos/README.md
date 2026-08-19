# ResearchOS

ResearchOS is the fork-specific orchestration layer that sits above the existing scientific Agent Skills library. It keeps `skills/` portable while adding persistent research memory, registries, decision logic, execution adapters, critique, measured-evidence ingestion, and confidence updates.

## Architecture

```text
Research Goal
    ↓
Persistent Knowledge Graph (SQLite nodes + typed edges)
    ↓
Evidence Ledger
    ↓
Hypothesis Registry
    ↓
Experiment Registry
    ↓
Decision Engine (next-best experiment)
    ↓
Research Orchestrator / Agent Dispatcher
    ↓
Scientific Agent Skills catalog
    ↓
Computational Experiment Adapter
    ↓
Independent Critic
    ↓
Physical Experiment (human/lab gated)
    ↓
Measured Evidence
    ↓
Bayesian confidence update
    ↓
Next-best experiment
```

## Design principles

- **Keep scientific skills unchanged.** ResearchOS lives outside `skills/` because upstream repository guidance intentionally rejects broad orchestrator skills.
- **Persist provenance.** Goals, evidence, hypotheses, experiments, runs, critiques, measurements, graph edges, and events are stored in SQLite.
- **Rank experiments, not truth.** The decision engine scores planned experiments using expected information gain, feasibility, budget efficiency, hypothesis uncertainty, and risk. It does not automatically accept or reject scientific hypotheses.
- **Bayesian updates are explicit.** Measurements carry a caller-supplied likelihood ratio. ResearchOS updates posterior probability but never invents an evidence likelihood.
- **Physical experiments stay gated.** ResearchOS can plan physical experiments and ingest their measurements, but only computational experiments have an automatic execution adapter.
- **Agent Skills are capabilities.** Agent tasks and computational experiments declare skill names; the catalog resolves those local `SKILL.md` definitions before dispatch.

## Quick start

```bash
python -m researchos init --db .researchos/research.db

python -m researchos goal \
  --db .researchos/research.db \
  --title "Passive daytime radiative cooling coating" \
  --question "Can the coating reduce internal horticultural storage temperature?" \
  --success "At least 3 C reduction under preregistered outdoor conditions"
```

The command returns a goal ID. Use it in subsequent commands:

```bash
python -m researchos evidence --db .researchos/research.db \
  --goal <GOAL_ID> \
  --claim "High solar reflectance is associated with lower daytime heat gain." \
  --source "doi:example" \
  --reliability 0.8 \
  --direction supporting

python -m researchos hypothesis --db .researchos/research.db \
  --goal <GOAL_ID> \
  --statement "A high-reflectance coating reduces daytime heat gain." \
  --mechanism "Reduced absorbed solar flux lowers envelope heat input." \
  --prior 0.5
```

Plan an experiment:

```bash
python -m researchos experiment --db .researchos/research.db \
  --goal <GOAL_ID> \
  --hypothesis <HYPOTHESIS_ID> \
  --title "Coupled optical-thermal simulation" \
  --kind computational \
  --cost 250 \
  --information-gain 0.8 \
  --feasibility 0.95 \
  --risk 0.05 \
  --skill hypothesis-generation
```

Choose the next experiment under a budget:

```bash
python -m researchos next --db .researchos/research.db \
  --goal <GOAL_ID> \
  --budget 1000
```

After independent review and measurement:

```bash
python -m researchos critique --db .researchos/research.db \
  --experiment <EXPERIMENT_ID> \
  --verdict proceed_with_caution \
  --issue "humidity sensitivity not yet tested" \
  --confidence 0.8

python -m researchos measure --db .researchos/research.db \
  --experiment <EXPERIMENT_ID> \
  --outcome "Observed result supports the preregistered prediction." \
  --likelihood-ratio 4 \
  --value 3.4 \
  --unit degC
```

## Python integration

```python
from researchos import ResearchOrchestrator, ResearchStore
from researchos.models import ExperimentKind

store = ResearchStore(".researchos/research.db")
research = ResearchOrchestrator(store)
```

For agent and simulator integrations, implement `ScientificAgent` from `researchos.agents` or `ComputationalExecutor` from `researchos.execution`. These interfaces deliberately do not prescribe an LLM provider, simulator, cloud, or lab platform.

## Testing

```bash
python -m pytest tests/_researchos -q
```

The dedicated `researchos-tests.yml` workflow runs this suite on changes to ResearchOS code or tests.
