---
name: flood-monitor-extract
description: Extract, geolocate, verify, deduplicate, and fuse raw FloodMonitor SourceRecord objects into auditable Observation and FloodEvent objects. Use for text or CCTV/image flood interpretation, time and place extraction, impact extraction, water-depth measurement or range inference, spatial uncertainty, cross-source matching, confidence assessment, verification status, evidence levels, and event consolidation.
---

# FloodMonitor Extract

Answer: "What actual flooding information can be extracted from the evidence?"

## Inputs

Require normalized `SourceRecord` objects. Keep source IDs and original evidence intact.

## Workflow

1. Decide whether each record contains direct flood evidence. Keep rainfall-only and warning-only records as context.
2. Create one or more `Observation` objects before constructing events.
3. Extract event type, time and precision, location text, geometry and precision, impacts, evidence text, and source references.
4. Extract explicit reported depth or infer a range from reference objects such as ankle, knee, tyre, wheel, bumper, vehicle door, or waist.
5. Mark each depth as measured/reported or inferred; retain method, basis, range, and confidence.
6. Interpret public CCTV/images when a configured vision method is available. Preserve frame time, camera location, visual basis, and temporal consistency.
7. Match observations using time, space, location semantics, event type, depth, and source independence.
8. Fuse matched observations into `FloodEvent` objects without over-merging nearby distinct incidents.

Use `flood_monitor.extract.ExtractionPipeline`, `flood_monitor.extractors`, and `flood_monitor.fusion`. The CLI stage is:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor extract --input-file source_records.json
```

## Outputs

Produce `Observation` and `FloodEvent` objects. Preserve source IDs, observation IDs, provenance, uncertainty, confidence, verification status, and evidence level as separate fields.

## Rules

- Never fabricate unavailable time, coordinates, depth, impacts, or verification.
- Never convert rainfall or a weather warning alone into a `FloodEvent`.
- Keep missing depth missing; do not synthesize depth from rainfall severity.
- Mark approximate locations and uncertainty; never present a district centroid as an exact point.
- Do not count copied or syndicated articles as independent corroboration.
- Keep confidence, `verification_status`, and `evidence_level` separate.

Pass `FloodEvent` objects to `flood-monitor-report`, `flood-monitor-model`, or `flood-monitor-drainage` as routed by `flood-monitor-agent`.
