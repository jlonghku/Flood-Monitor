---
name: flood-monitor-report
description: Generate clear, interactive, auditable FloodMonitor products from SourceRecord, Observation, FloodEvent, FloodField, DrainageAssessment, and RunManifest objects. Use for Traditional Chinese Hong Kong flood maps, structured JSON, event and evidence lists, diagnostics, provenance tables, model and forecast layers, drainage layers, and report regeneration from existing canonical data.
---

# FloodMonitor Report

Answer: "How should the flood intelligence results be presented and audited?"

## Inputs

Accept any canonical FloodMonitor objects. Do not reinterpret sources or generate new model results while reporting.

## Workflow

1. Validate object types, schema versions, provenance links, and layer timestamps.
2. Build event, observation, source, model, forecast, hotspot, and drainage layers that are available.
3. Render local-language labels; use Traditional Chinese for Hong Kong.
4. Expose source URLs, original evidence, methods, uncertainty, verification, evidence level, model version, run ID, horizon, and warnings.
5. Preserve compatibility with the existing `flood_data.json`, `map.html`, and `template.html` workflow.

Use `flood_monitor.gis.FloodMap` and `flood_monitor.render_html`. The CLI stage is:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor report --events-file flood_data.json --output-dir outputs/report
```

## Outputs

Keep these compatible outputs:

- `flood_data.json`: canonical report database.
- `map.html`: self-contained interactive report.
- `template.html`: HTML reader for same-directory JSON.

Also emit canonical sidecars when available: `observations.json`, `model_results.json`, `drainage_results.json`, `run_manifest.json`, and diagnostics.

## Rules

- Label direct source facts, text inference, visual inference, geolocation estimates, fused events, reconstruction, simulation, forecasts, and drainage hypotheses distinctly.
- Do not hide missing depth, approximate location, source failures, or model warnings.
- Keep a table fallback when Leaflet or map tiles are unavailable.
- Do not present a forecast layer as a current observation.

Receive inputs from the other FloodMonitor Skills or invoke `flood-monitor-agent` for routing.
