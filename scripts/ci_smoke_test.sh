#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTIFACT_DIR=$(mktemp -d)
BUILD_VENV="$ARTIFACT_DIR/build-venv"
INSTALL_VENV="$ARTIFACT_DIR/install-venv"
DIST_DIR="$ARTIFACT_DIR/dist"
cleanup() {
  rm -rf "$ARTIFACT_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

python -m venv "$BUILD_VENV"
"$BUILD_VENV/bin/python" -m pip install --upgrade pip build
"$BUILD_VENV/bin/python" -m build --outdir "$DIST_DIR"

WHEEL_PATH=$(
  DIST_DIR="$DIST_DIR" "$BUILD_VENV/bin/python" - <<'PY'
import os
from pathlib import Path
wheels = sorted(Path(os.environ['DIST_DIR']).glob('oci_vision_ai-*.whl'))
if not wheels:
    raise SystemExit('No wheel found in dist/')
print(wheels[-1].resolve())
PY
)

python -m venv "$INSTALL_VENV"
"$INSTALL_VENV/bin/python" -m pip install --upgrade pip
"$INSTALL_VENV/bin/pip" install "$WHEEL_PATH"

cd "$ARTIFACT_DIR"

"$INSTALL_VENV/bin/oci-vision" --help >/dev/null
"$INSTALL_VENV/bin/oci-vision" analyze dog_closeup.jpg --demo --output-format json > analyze.json
"$INSTALL_VENV/bin/oci-vision" compare dog_closeup.jpg sign_board.png --demo --output-format json > compare.json
"$INSTALL_VENV/bin/oci-vision" batch dog_closeup.jpg sign_board.png invoice_demo.png --demo --output-format json > batch.json
"$INSTALL_VENV/bin/oci-vision" cockpit --demo --image dog_closeup.jpg --features classification,detection --screenshot cockpit.svg >/dev/null

"$INSTALL_VENV/bin/python" - <<'PY'
import json
from pathlib import Path
from oci_vision.gallery import load_manifest
from oci_vision.web.app import create_app

payload = json.loads(Path('analyze.json').read_text())
assert payload['classification']['labels'][0]['name'] == 'Dog', payload
assert payload['available_features'] == ['classification', 'detection'], payload['available_features']
assert payload['insights'], 'analyze insights missing'
comparison = json.loads(Path('compare.json').read_text())
assert 'classification' in comparison['left_only_features'], comparison
assert 'text' in comparison['right_only_features'], comparison
batch = json.loads(Path('batch.json').read_text())
assert batch['report_count'] == 3, batch
assert batch['feature_coverage']['classification'] >= 1, batch['feature_coverage']
svg = Path('cockpit.svg')
assert svg.exists(), 'cockpit.svg was not created'
text = svg.read_text(encoding='utf-8')
assert '<svg' in text, 'cockpit.svg does not look like SVG output'
app = create_app(demo=True)
manifest = load_manifest()
assert app.title == 'OCI Vision Studio', app.title
assert manifest['images'][0]['filename'] == 'dog_closeup.jpg', manifest['images'][0]
print('Smoke test passed')
PY
