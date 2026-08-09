---
name: flood-monitor-model
description: Reconstruct current inundation and generate model-based short-term flood forecasts from FloodMonitor observations, events, forcing, terrain, drainage, boundary conditions, and configured hydraulic or surrogate models. Use for observation-constrained flood-state reconstruction, data assimilation, scenario matching, hydraulic resimulation, or forecasts for now and +1/+3/+6 hours.
---

# FloodMonitor Model

Answer: "What is the model-consistent spatial flood state now, and what may happen next?"

## Inputs

Require relevant `Observation` and `FloodEvent` objects plus adequate model inputs: terrain, drainage representation, rainfall/nowcast, tide, boundary conditions, prior state, and a configured `HydraulicModelAdapter`.

## Workflow

1. Validate that the adapter, forcing, spatial domain, timestamps, and boundary data are configured.
2. Reconstruct the current state from observations using the adapter.
3. Forecast only requested horizons, normally now, +1 h, +3 h, or +6 h.
4. Return canonical `FloodField` objects with model name/version, valid time, horizon, run ID, constraints, and uncertainty.
5. Record warnings and failures in the `RunManifest`.

Use `flood_monitor.model.HydraulicModelAdapter` and `flood_monitor.model.FloodModelPipeline`. The CLI stage is:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor model --events-file flood_data.json --forecast-horizon 1
```

## Rules

- Never present reconstruction, simulation, or forecast as observed flooding.
- Never invent a working hydraulic result when no adapter or required forcing exists.
- Fail with explicit "not configured" guidance when model execution is unavailable.
- Keep the Skill model-agnostic; integrate SWMM, ANUGA, LISFLOOD-FP, FASTFLOOD, or other engines behind adapters.
- Preserve uncertainty and all observation constraints.

Pass `FloodField` outputs to `flood-monitor-report` and, when needed, `flood-monitor-drainage`. CCTV interpretation remains in `flood-monitor-extract`.
