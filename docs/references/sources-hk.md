# Hong Kong Source Notes

Flood Monitor should prioritize source adapters that preserve provenance and can operate in online or offline/demo modes.

## Government And Monitoring Sources

- HKO rainfall: station rainfall, automatic weather station metadata, warnings, radar-derived rainfall if available.
- DSD flooding and water-level data: flooding blackspots, water-level monitoring, drainage reports, and official incident feeds when accessible.
- DATA.GOV.HK: catalog-backed source discovery for HKO, DSD, HyD, LandsD, CEDD, and other departments.
- Tide and coastal data: tide gauges and storm-surge-relevant water levels from official marine sources.

## Implemented HKO Live Adapter

`HKOSource` reads the HKO current weather open-data JSON endpoint:

`https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en`

It currently extracts past-hour district rainfall, official warning messages, approximate district centroid coordinates, rainfall threshold filtering, and whole-Hong-Kong warning bounding boxes. It also supports warning summary mode:

`https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=warnsum&lang=en`

Treat these as live monitoring evidence, not archive APIs.

## Media Sources

Track source name, URL, publication time, article title, body, images, and quoted locations. Good first targets include Hong Kong 01, Ming Pao, Oriental Daily/on.cc, Wen Wei Po, RTHK, SCMP, and TVB News. Respect robots, paywalls, and licensing.

Implemented generic adapters:

- `RSSFeedSource`: scans RSS/Atom feeds for flood/rainstorm keywords and converts matching items into `news` evidence.
- `WebArticleSource`: parses public article URLs with standard HTML metadata and paragraphs.
- `LocalFileEvidenceSource`: imports analyst/user CSV or JSON exports with optional `depth_m`, `lon`, `lat`, `observed_time`, source fields, and URLs.
- `GeoJSONSource`: imports flood extent polygons or observation features from local or URL GeoJSON.
- `ArcGISFeatureServerSource`: reads public ArcGIS FeatureServer layers through `/query?f=geojson`.

## Social Sources

Threads, Facebook, Xiaohongshu, Weibo, Telegram, LIHKG, and similar platforms should be treated as evidence streams. Prefer official APIs or user-provided exports. Store author handles only when policy and downstream use allow it.

## Remote Sensing

Sentinel-1 is preferred for cloud-robust flood extent. Sentinel-2 can support optical water indices when clouds permit. Store acquisition time, orbit/tile, processing baseline, cloud score, algorithm, threshold, and output polygon confidence.

## User Uploads

Uploaded photos should keep local path, EXIF time/GPS if available, analyst notes, reference-object depth estimate, and privacy flags. Do not infer exact personal locations beyond what the task requires.
