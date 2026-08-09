# Validation Export

Flood Monitor exports validation bundles for hydrodynamic and drainage model verification.

## Common Bundle

Each export should include:

- `event.json`: full canonical FloodEvent.
- `flood_extent.geojson`: observed flood polygon or FeatureCollection.
- `depth_points.csv`: observed water depths with time, coordinates, uncertainty, method, reference object, and evidence IDs.
- `water_levels.csv`: station water-level time series.
- `rainfall.csv`: rainfall time series by station/grid cell and accumulation window.
- `evidence_manifest.csv`: provenance index for photos, news, social posts, government data, and remote-sensing scenes.

## Target Model Notes

- SWMM: emphasize rainfall time series, node/link surcharge or observed depth points near junctions/outfalls, and event time windows.
- ANUGA: emphasize flood extent polygons, water-depth points, boundary/tide records, and DEM-aligned coordinates.
- LISFLOOD-FP: emphasize raster-compatible flood extent/depth observations and hydrographs.
- TELEMAC: emphasize boundary conditions, tide/water level records, extent polygons, and point depth observations.
- D-HYDRO: emphasize coupled rainfall, tide, water-level, and urban drainage observations.

## Export Rules

- Do not silently drop uncertain observations; include uncertainty columns.
- Preserve WGS84 GeoJSON and add target-CRS notes rather than reprojecting without explicit instruction.
- Use ISO 8601 timestamps in CSV files.
- Include a `README.txt` in generated bundles describing files, event ID, creation time, and known limitations.
