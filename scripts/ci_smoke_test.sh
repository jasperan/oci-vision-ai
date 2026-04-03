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
"$INSTALL_VENV/bin/oci-vision" config --demo >/dev/null
"$INSTALL_VENV/bin/oci-vision" search-runs invoice > search-runs.json
"$INSTALL_VENV/bin/oci-vision" analyze dog_closeup.jpg --demo --output-format json > analyze.json
"$INSTALL_VENV/bin/oci-vision" detect dog_closeup.jpg --demo --output-format json > detect.json
"$INSTALL_VENV/bin/oci-vision" ocr sign_board.png --demo --output-format json > ocr.json
"$INSTALL_VENV/bin/oci-vision" document invoice_demo.png --demo --output-format json > document.json
"$INSTALL_VENV/bin/oci-vision" compare dog_closeup.jpg sign_board.png --demo --output-format json > compare.json
"$INSTALL_VENV/bin/oci-vision" batch dog_closeup.jpg sign_board.png invoice_demo.png --demo --output-format json > batch.json
"$INSTALL_VENV/bin/oci-vision" showcase --demo --output-dir showcase --output-format json > showcase.json
"$INSTALL_VENV/bin/oci-vision" cockpit --demo --image dog_closeup.jpg --features classification,detection --screenshot cockpit.svg >/dev/null

"$INSTALL_VENV/bin/python" - <<'PY'
import json
from pathlib import Path
from oci_vision.gallery import load_manifest
from oci_vision.web.app import _STATIC_DIR, _TEMPLATE_DIR, create_app

payload = json.loads(Path('analyze.json').read_text())
assert payload['classification']['labels'][0]['name'] == 'Dog', payload
assert payload['available_features'] == ['classification', 'detection'], payload['available_features']
assert payload['insights'], 'analyze insights missing'
Path('detect-result.json').write_text(json.dumps(json.loads(Path('detect.json').read_text())['detection'], indent=2))
Path('ocr-result.json').write_text(json.dumps(json.loads(Path('ocr.json').read_text())['text'], indent=2))
Path('document-result.json').write_text(json.dumps(json.loads(Path('document.json').read_text())['document'], indent=2))
assert json.loads(Path('search-runs.json').read_text()) == []
comparison = json.loads(Path('compare.json').read_text())
assert 'classification' in comparison['left_only_features'], comparison
assert 'text' in comparison['right_only_features'], comparison
batch = json.loads(Path('batch.json').read_text())
assert batch['report_count'] == 3, batch
assert batch['feature_coverage']['classification'] >= 1, batch['feature_coverage']
showcase = json.loads(Path('showcase.json').read_text())
assert showcase['asset_count'] >= 4, showcase
assert (Path('showcase') / 'index.html').exists(), 'showcase index missing'
assert (Path('showcase') / 'showcase.json').exists(), 'showcase summary missing'
svg = Path('cockpit.svg')
assert svg.exists(), 'cockpit.svg was not created'
text = svg.read_text(encoding='utf-8')
assert '<svg' in text, 'cockpit.svg does not look like SVG output'
app = create_app(demo=True)
manifest = load_manifest()
assert app.title == 'OCI Vision Studio', app.title
assert manifest['images'][0]['filename'] == 'dog_closeup.jpg', manifest['images'][0]
base_template = Path(_TEMPLATE_DIR) / 'base.html'
base_html = base_template.read_text(encoding='utf-8')
assert '/static/styles.css' in base_html, base_html[:200]
assert '/static/htmx-2.0.0.min.js' in base_html, base_html[:200]
assert 'cdn.tailwindcss.com' not in base_html, base_html[:200]
assert 'unpkg.com/htmx.org' not in base_html, base_html[:200]
static_dir = Path(_STATIC_DIR)
assert (static_dir / 'styles.css').exists(), static_dir
assert (static_dir / 'htmx-2.0.0.min.js').exists(), static_dir
print('Smoke test passed')
PY

"$INSTALL_VENV/bin/oci-vision" eval detection detect-result.json detect-result.json --output-format json > eval-detection.json

"$INSTALL_VENV/bin/python" - <<'PY'
import json
from pathlib import Path
eval_detection = json.loads(Path('eval-detection.json').read_text())
assert eval_detection['precision'] == 1.0, eval_detection
assert eval_detection['recall'] == 1.0, eval_detection
assert eval_detection['mean_iou'] == 1.0, eval_detection
print('Eval smoke passed')
PY
