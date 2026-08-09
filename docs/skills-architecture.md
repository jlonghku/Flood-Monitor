# FloodMonitor Skills Architecture

## System map

```text
FloodMonitor-HK
       |
flood-monitor-agent
       |
       +-- flood-monitor-collect
       +-- flood-monitor-extract
       +-- flood-monitor-model
       +-- flood-monitor-drainage
       +-- flood-monitor-report
```

The repository is one `flood-monitor` Codex Plugin. Its Skills are thin semantic and orchestration layers. The shared Python package under `src/flood_monitor/` owns acquisition, parsing, extraction, geospatial operations, fusion, model interfaces, drainage analysis, rendering, and provenance.

## Data flow

```text
External Sources
      |
 SourceRecord             raw, normalized, auditable source item
      |
flood-monitor-extract
      |
 Observation              one extracted piece of flood evidence
      |
 FloodEvent               consolidated real-world event hypothesis
      |\
      | +-- flood-monitor-report
      |
      +---- flood-monitor-model --> FloodField
      |                              |
      |                              +-- report / drainage
      |
      +---- flood-monitor-drainage --> DrainageAssessment
```

A `RunManifest` spans an end-to-end run and records scope, Skills used, counts, warnings, errors, versions, configuration, and outputs.

## Boundaries

- **collect = acquisition.** Fetch public or user-provided material and normalize it. Never decide that a flood happened.
- **extract = interpretation and event construction.** Create observations only from direct flood evidence, then geolocate, verify, deduplicate, and fuse them.
- **model = reconstruction and forecast.** Produce model-derived spatial fields through adapters. Never relabel a model field as an observation.
- **drainage = diagnosis.** Summarize recurrence and evaluate infrastructure associations. Distinguish association, hypothesis, model support, and confirmed cause.
- **report = visualization and auditability.** Render existing canonical objects without changing their scientific meaning.
- **agent = orchestration.** Select the minimum necessary stages and preserve structured handoffs.

## Scientific invariants

1. Rainfall, radar, and weather warnings alone cannot create a `FloodEvent`.
2. Direct evidence, inference, reconstruction, simulation, forecast, and diagnosis remain distinguishable.
3. Approximate time, location, and depth retain explicit uncertainty.
4. Source and processing provenance survive every transformation.
5. Drainage proximity is not proof of causality.
6. No collector bypasses access controls.

## Compatibility

The package remains importable with `PYTHONPATH=src`, and the original `python -m flood_monitor.monitor --demo`, `--live-hk`, and `--multisource` flags remain accepted. An editable install also exposes the `flood-monitor` command. `flood_data.json` keeps the legacy `events`, `sources`, and `geojson` keys while schema version 2 adds source records, observations, model results, drainage results, and the run manifest.

The model layer currently provides a real adapter contract and explicit unconfigured errors; it does not ship a hydraulic engine. CCTV acquisition and interpretation have stable semantic homes, but automated CV is not claimed unless a vision implementation is configured.
