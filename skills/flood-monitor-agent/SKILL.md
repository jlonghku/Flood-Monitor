---
name: flood-monitor-agent
description: Coordinate FloodMonitor-HK workflows and invoke only the minimum required collect, extract, model, drainage, and report Skills. Use for end-to-end requests to find reported flooding, build an event database, combine news or CCTV evidence, estimate current inundation, forecast 1/3/6 hours ahead, identify recurrent hotspots, diagnose possible drainage bottlenecks, or generate a flood intelligence report.
---

# FloodMonitor Agent

Act as the user-facing orchestration layer. Do not scrape, extract, model, diagnose, or render directly.

## Inputs

Resolve the requested region, time range, optional bbox, source types, output language, requested products, forecast horizons, and available model/drainage inputs. Ask only when a missing choice materially changes the result.

## Route the minimum workflow

- Event search or database: `collect -> extract -> report`.
- Current inundation reconstruction: `collect -> extract -> model -> report`.
- Short-term forecast: `collect -> extract -> model -> report`.
- Drainage diagnosis: `collect -> extract -> model` when hydraulic evidence is required, then `drainage -> report`.
- Historical hotspot summary: `collect -> extract -> drainage -> report`; skip model unless requested or needed.
- Report from existing canonical objects: invoke only `report`.

Use `flood_monitor.orchestration.routing.route_skills` to make deterministic routing decisions in code-backed workflows.

## Data handoff

Pass only canonical objects:

`SourceRecord -> Observation -> FloodEvent -> FloodField -> DrainageAssessment`

Create one `RunManifest` per end-to-end run. Preserve source IDs, observation IDs, model run IDs, warnings, errors, configuration, and output paths.

## Rules

- Never allow rainfall, radar, or weather warnings alone to create a `FloodEvent`.
- Keep observed, text-inferred, image-inferred, fused, reconstructed, simulated, forecast, and diagnostic results visibly distinct.
- Skip model execution when event evidence or a historical count is sufficient.
- Do not claim drainage causality from proximity alone.
- Do not bypass access controls, login walls, paywalls, CAPTCHAs, or private platforms.
- Report unavailable model or drainage inputs explicitly; never fabricate outputs.

## Shared implementation

From the plugin root, use the shared package under `src/flood_monitor`. The stable CLI is:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor run --region "Hong Kong" --start-time START --end-time END
```

The other five `flood-monitor-*` Skills own their respective stages.
