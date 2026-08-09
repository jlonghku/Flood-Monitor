---
name: flood-monitor-collect
description: Acquire and normalize raw flood-relevant information into SourceRecord objects without deciding that flooding occurred. Use for public news, government pages, flood incident records, RSS/Atom, public social or community reports, article URLs, user text, CSV/JSON/GeoJSON, ArcGIS, HKO rainfall and warnings, DSD/open data, CCTV metadata or frames, water-level sensors, IoT observations, and other public or user-provided sources.
---

# FloodMonitor Collect

Answer: "What source information is available?"

## Inputs

Accept region, start/end time, optional bbox, source selection, URLs, local files, API configuration, and collection limits. Use local-language and English queries where discovery is performed. For Hong Kong, prioritize the source seeds in `../../docs/references/sources-hk.md`.

## Workflow

1. Acquire only public or user-authorized data.
2. Preserve raw text, media references, provided geometry, timestamps, retrieval status, and provenance.
3. Normalize each item into `flood_monitor.schemas.SourceRecord`.
4. Generate deterministic source IDs and deduplicate repeated acquisition of the same item.
5. Record source failures without discarding successful records unless strict mode is requested.
6. Return source counts and diagnostics alongside the records.

Use `flood_monitor.collect.CollectionPipeline` and adapters under `flood_monitor.sources`. The CLI stage is:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor collect [source options]
```

## Outputs

Produce `SourceRecord` objects and, for CLI runs, `source_records.json` plus `run_manifest.json`.

Do not emit `Observation` or `FloodEvent` objects.

## Scientific and access rules

- Treat rainfall, radar, warnings, and meteorological conditions as context only.
- Preserve HKO rainfall and warning data, but do not label ordinary warnings as flood events.
- Collect CCTV here; interpret its pixels in `flood-monitor-extract`.
- Do not infer missing event facts during collection.
- Do not bypass login requirements, paywalls, robots restrictions, CAPTCHAs, or anti-abuse controls.
- Treat GDELT as supplemental; on HTTP 429, stop aggressive retries and use other public routes.

Pass results to `flood-monitor-extract`. Invoke `flood-monitor-agent` for end-to-end routing.
