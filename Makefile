# Aiwan-e-Jamhoor — data & map pipeline (run from the project root).
#
#   make results   -> data/results_all.json
#   make geometry  -> reconstructed baseline boundaries (2018 & 2023)
#   make app       -> assemble the map application
#   make serve     -> preview the site at http://localhost:8000
#
# WARNING: `make app` assumes scripts/build_map.py's 2018 input path has been
# corrected to data/na_2018delim_v2.geojson. The shipped 2024 layer was swapped
# in surgically by scripts/patch_app_2024.py to AVOID regressing 2018 — read the
# README "build gotchas" before a full rebuild. The true-boundary digitisation
# steps (METHODOLOGY.md §4–§5) need the ECP map-sheet archives and are run per
# province via the run_*/compose_*/digitise_* scripts; they are not in `all`.

PY := python3

.PHONY: all results geometry app serve

all: results geometry app

results:
	$(PY) scripts/build_results_json.py

geometry:
	$(PY) scripts/build_reconstructed_geometry.py
	mapshaper na_2018delim_raw.geojson -simplify 15% keep-shapes -clean \
		-o precision=0.0001 data/na_2018delim_simplified.geojson
	mapshaper na_2024delim_raw.geojson -simplify 15% keep-shapes -clean \
		-o precision=0.0001 na_2024delim_simplified.geojson

app:
	$(PY) scripts/build_2024_layer.py
	$(PY) scripts/build_map.py

serve:
	$(PY) -m http.server 8000
