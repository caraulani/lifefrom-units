#!/usr/bin/env bash
# Single build command: regenerate every output from the raw sources, then run both test suites.
#   ./scripts/build_all.sh            (uses raw files already in ../_raw)
#   ./scripts/build_all.sh --fetch    (downloads the raw sources first)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "${1:-}" == "--fetch" ]]; then ./scripts/fetch_sources.sh; fi

python3 -I scripts/build.py              # data/units.json, data/*.csv, web/lifefrom-units.json, package data
python3 -I scripts/make_vectors.py       # tests/vectors.json (expected values computed independently)

(cd python && uv run --quiet --with pytest --with-editable . python -m pytest -q)
(cd python && uv run --quiet --python 3.9 --isolated --with pytest --with-editable . python -m pytest -q)
(cd ts && npm install --no-audit --no-fund --silent && npm test --silent 2>&1 | tail -8)
python3 -I scripts/crosscheck_languages.py

(cd python && rm -rf dist && uv build --quiet)
(cd ts && npm pack --silent --pack-destination "$ROOT/ts" >/dev/null)

# checksums of every repository file (build artefacts and caches excluded)
find . -type f -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/dist/*' \
  -not -path '*/__pycache__/*' -not -path '*/.pytest_cache/*' -not -path '*/.venv/*' -not -path '*.egg-info/*' \
  -not -name '*.tgz' -not -name '.DS_Store' -not -name SHA256SUMS | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS
echo "build complete"
