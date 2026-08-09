# FloodMonitor

FloodMonitor is one Codex Plugin containing six focused Skills and one shared Python package:

`COLLECT -> EXTRACT -> MODEL -> DRAINAGE -> REPORT`

`flood-monitor-agent` selects the minimum stages required by a request. Collection normalizes raw sources; extraction alone may turn direct flood evidence into observations and events. Model and drainage stages never masquerade as observations.

## Skills

- `flood-monitor-agent`: orchestration and routing.
- `flood-monitor-collect`: source acquisition and `SourceRecord` normalization.
- `flood-monitor-extract`: evidence interpretation, observations, geolocation, depth inference, deduplication, and event fusion.
- `flood-monitor-model`: adapter-based reconstruction and short-term forecast interfaces.
- `flood-monitor-drainage`: hotspot and evidence-labelled drainage association analysis.
- `flood-monitor-report`: interactive maps, JSON, provenance, diagnostics, model/forecast, and drainage layers.

See [docs/skills-architecture.md](docs/skills-architecture.md) for boundaries and data flow.

## Repository layout

```text
Flood-Monitor/
├── .codex-plugin/plugin.json  # Plugin manifest
├── skills/                    # Six Codex Skills
├── src/flood_monitor/         # Shared implementation
├── tests/                     # Automated tests
├── docs/                      # Architecture and shared references
└── pyproject.toml             # Python package and CLI
```

## CLI

Run directly from the repository with `PYTHONPATH=src`, or install an editable CLI with `python3 -m pip install -e .`. The original flag-based interface remains valid and positional stages are also available:

```bash
PYTHONPATH=src python3 -m flood_monitor.monitor --demo
PYTHONPATH=src python3 -m flood_monitor.monitor run --multisource --input-file evidence.json --output-dir outputs/run
PYTHONPATH=src python3 -m flood_monitor.monitor collect --rss-url "https://example.org/feed.xml" --output-dir outputs/collect
PYTHONPATH=src python3 -m flood_monitor.monitor extract --input-file source_records.json --output-dir outputs/extract
PYTHONPATH=src python3 -m flood_monitor.monitor report --events-file flood_data.json --output-dir outputs/report
```

`model` requires a configured `HydraulicModelAdapter`; it fails explicitly rather than fabricating a result. `drainage` can summarize hotspots and spatial associations, but does not claim causality without stronger evidence.

## Compatible outputs

`flood_data.json`, `map.html`, and `template.html` remain supported. Modular runs also write `observations.json` and `run_manifest.json`; model and drainage sidecars are written when those stages run.
