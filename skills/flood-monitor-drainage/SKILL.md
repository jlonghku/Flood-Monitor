---
name: flood-monitor-drainage
description: Analyze recurrent FloodMonitor events and their relationship with drainage infrastructure to identify flood hotspots, vulnerable assets, and plausible drainage bottlenecks. Use for historical hotspot analysis, drainage-network association, inlet or pipe capacity hypotheses, surcharge, backwater, pump or tidal influence, low-lying-road vulnerability, risk ranking, and evidence-labelled follow-up recommendations.
---

# FloodMonitor Drainage

Answer: "Why may flooding recur here, and which drainage components warrant investigation?"

## Inputs

Use historical `FloodEvent` records and, when available, `FloodField` results, drainage networks, inlets, manholes, pipes, channels, pumps, terrain, surcharge indicators, downstream levels, and tides.

## Workflow

1. Quantify recurrence, depth, duration, and observation coverage by spatial unit.
2. Associate events or fields with drainage assets using explicit spatial and network criteria.
3. Evaluate available model indicators and boundary conditions.
4. Form evidence-labelled diagnostic hypotheses.
5. Return `DrainageAssessment` objects with confidence, evidence, conclusion level, and follow-up actions.

Use `flood_monitor.drainage.DrainageAnalyzer`. The CLI stage is:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor drainage --events-file flood_data.json
```

## Rules

- Separate `association`, `diagnostic_hypothesis`, `model_supported`, and `confirmed_cause` conclusions.
- Never claim that a nearby drain caused flooding solely because of proximity.
- State when drainage assets, condition data, capacity data, or model outputs are missing.
- Normalize recurrence conclusions against source and observation coverage when possible.
- Preserve every supporting event, field, asset, and processing method in provenance.

Pass assessments to `flood-monitor-report`. Invoke `flood-monitor-model` only when hydraulic evidence is required; hotspot counting alone may skip it.
