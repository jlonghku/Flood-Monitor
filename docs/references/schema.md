# FloodMonitor Canonical Data Contracts

The authoritative typed implementations live in `src/flood_monitor/schemas/` and serialize to JSON.

## SourceRecord

Store normalized raw source material: stable source ID, source type, publisher/provider, title, URL, publication/retrieval times, raw text, language, media, provided geometry, metadata, retrieval status, and provenance. Legacy Evidence field aliases remain during migration.

## Observation

Store one extracted piece of actual flood evidence: source ID, observation/event type, observed time and precision, location text and geometry, spatial precision and uncertainty, optional depth with method and range, impacts, original evidence text, extraction method/confidence, and provenance.

## FloodEvent

Store a consolidated event hypothesis: event time, type, region, status, severity, confidence, verification status, evidence level, spatial representation, depths, hydro-meteorological context, observation/source IDs, evidence records, and fusion provenance.

Confidence, verification status, and evidence level are separate concepts. Rainfall-only records never create events. Missing depth remains missing.

## FloodField

Store model-derived reconstruction or forecast fields: valid time, horizon, raster/geometry, depth/extent/velocity where available, model and version, observation constraints, uncertainty, run ID, provenance, and result kind.

## DrainageAssessment

Store hotspot and drainage findings: spatial unit, associated assets, flood history, model indicators, diagnostic hypotheses, confidence, evidence, follow-up, provenance, and conclusion level.

## RunManifest

Store reproducibility data: run ID, timestamps, requested scope, Skills used, counts, model runs, warnings/errors, software version, non-secret configuration, and output paths.

## Spatial and uncertainty rules

- Use WGS84 `[lon, lat]` unless CRS metadata explicitly states otherwise.
- Represent approximate areas as areas, not exact points.
- Mark text/image reference-object depth as inferred and retain a range.
- Keep direct source facts, extraction inference, model output, forecast, and drainage hypotheses distinguishable.
