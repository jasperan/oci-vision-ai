#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARTIFACT_DIR="${OCI_VISION_WALKTHROUGH_DIR:-$(mktemp -d)}"
PORT="${OCI_VISION_WALKTHROUGH_PORT:-8010}"
KEEP_ARTIFACTS="${OCI_VISION_WALKTHROUGH_KEEP:-0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$ARTIFACT_DIR/venv"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  if [[ "$KEEP_ARTIFACTS" != "1" ]]; then
    rm -rf "$ARTIFACT_DIR"
  fi
}
trap cleanup EXIT

cd "$ROOT_DIR"

echo "==> Creating walkthrough environment in $ARTIFACT_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
if ! pip install -e ".[dev]"; then
  echo "==> Retrying editable install after transient pip failure"
  pip install -e ".[dev]"
fi

mkdir -p "$ARTIFACT_DIR/cli" "$ARTIFACT_DIR/web"

echo "==> Running CLI walkthrough"
pushd "$ARTIFACT_DIR/cli" >/dev/null
oci-vision --help > help.txt
oci-vision config --demo > config-demo.txt
oci-vision gallery > gallery.txt
oci-vision search-runs invoice > search-runs.json
oci-vision analyze dog_closeup.jpg --demo > analyze-rich.txt
oci-vision analyze dog_closeup.jpg --demo --output-format json > analyze.json
oci-vision analyze dog_closeup.jpg --demo --output-format html > analyze-html.txt
oci-vision analyze dog_closeup.jpg --demo --save-overlay "$ARTIFACT_DIR/cli/analyze-overlay.png" > analyze-overlay.txt
oci-vision classify dog_closeup.jpg --demo --output-format json > classify.json
oci-vision detect dog_closeup.jpg --demo --output-format json > detect.json
oci-vision ocr sign_board.png --demo --output-format json > ocr.json
oci-vision faces portrait_demo.png --demo --output-format json > faces.json
oci-vision document invoice_demo.png --demo --output-format json > document.json
oci-vision compare dog_closeup.jpg sign_board.png --demo --output-format json > compare.json
oci-vision batch dog_closeup.jpg sign_board.png invoice_demo.png --demo --output-format json > batch.json
oci-vision workflow receipt invoice_demo.png --demo > workflow-receipt.json
oci-vision workflow shelf dog_closeup.jpg --demo > workflow-shelf.json
oci-vision workflow inspection dog_closeup.jpg --demo > workflow-inspection.json
oci-vision workflow archive-search invoice_demo.png --demo --query INV-1001 > workflow-archive-search.json

python - <<'PY'
import json
from pathlib import Path

for source_name, field_name, target_name in [
    ("detect.json", "detection", "detect-result.json"),
    ("ocr.json", "text", "ocr-result.json"),
    ("document.json", "document", "document-result.json"),
]:
    payload = json.loads(Path(source_name).read_text())
    Path(target_name).write_text(json.dumps(payload[field_name], indent=2), encoding="utf-8")
PY

oci-vision eval detection detect-result.json detect-result.json --output-format json > eval-detection.json
oci-vision eval text ocr-result.json ocr-result.json --output-format json > eval-text.json
oci-vision eval document document-result.json document-result.json --output-format json > eval-document.json
oci-vision showcase --demo --output-format json > showcase.json
oci-vision showcase --demo --output-dir "$ARTIFACT_DIR/showcase" --output-format html > showcase-html.txt
oci-vision cockpit --demo --image dog_closeup.jpg --features classification,detection --screenshot "$ARTIFACT_DIR/cli/cockpit.svg" > /dev/null
popd >/dev/null

python - <<PY
import json
from pathlib import Path

artifact_dir = Path("$ARTIFACT_DIR")
analyze = json.loads((artifact_dir / "cli" / "analyze.json").read_text())
search_runs = json.loads((artifact_dir / "cli" / "search-runs.json").read_text())
eval_detection = json.loads((artifact_dir / "cli" / "eval-detection.json").read_text())
showcase = json.loads((artifact_dir / "cli" / "showcase.json").read_text())
assert analyze["classification"]["labels"][0]["name"] == "Dog", analyze
assert search_runs == [], search_runs
assert eval_detection["precision"] == 1.0, eval_detection
assert eval_detection["recall"] == 1.0, eval_detection
assert eval_detection["mean_iou"] == 1.0, eval_detection
assert showcase["asset_count"] >= 4, showcase
assert showcase["workflows"]["receipt"]["fields"]["Invoice Number"] == "INV-1001", showcase
assert (artifact_dir / "showcase" / "index.html").exists()
assert (artifact_dir / "showcase" / "showcase.json").exists()
assert (artifact_dir / "cli" / "dog_closeup_report.html").exists()
assert (artifact_dir / "cli" / "cockpit.svg").exists()
assert (artifact_dir / "cli" / "analyze-overlay.png").exists()
print("CLI walkthrough assertions passed")
PY

echo "==> Launching web dashboard"
oci-vision web --demo --host 127.0.0.1 --port "$PORT" > "$ARTIFACT_DIR/web/server.log" 2>&1 &
SERVER_PID=$!

python - <<PY
import time
import httpx

base_url = "http://127.0.0.1:$PORT"
for _ in range(60):
    try:
        response = httpx.get(base_url + "/", timeout=2.0)
        if response.status_code == 200:
            break
    except Exception:
        time.sleep(0.5)
else:
    raise SystemExit("web server did not become ready")
PY

python - <<PY
from pathlib import Path
import httpx

base_url = "http://127.0.0.1:$PORT"
root = Path("$ROOT_DIR")
image_path = root / "src" / "oci_vision" / "gallery" / "images" / "dog_closeup.jpg"

with httpx.Client(base_url=base_url, timeout=10.0) as client:
    assert client.get("/").status_code == 200
    assert client.get("/gallery").status_code == 200
    assert client.get("/showcase").status_code == 200
    assert client.get("/report/dog_closeup.jpg").status_code == 200
    assert client.get("/compare", params={"left": "dog_closeup.jpg", "right": "sign_board.png"}).status_code == 200
    gallery_resp = client.get("/api/gallery")
    gallery_resp.raise_for_status()
    assert len(gallery_resp.json()["images"]) >= 4
    search_resp = client.get("/api/search", params={"query": "invoice"})
    search_resp.raise_for_status()
    assert search_resp.json()["results"] == []
    analyze_resp = client.post("/api/analyze", json={"image": "dog_closeup.jpg", "features": ["classification", "detection"]})
    analyze_resp.raise_for_status()
    analyze_payload = analyze_resp.json()
    assert analyze_payload["classification"]["labels"][0]["name"] == "Dog"
    with image_path.open("rb") as handle:
        upload_resp = client.post(
            "/api/analyze-upload",
            files={"file": ("dog_closeup.jpg", handle, "image/jpeg")},
            data={"features": "classification,detection"},
        )
    upload_resp.raise_for_status()
    upload_payload = upload_resp.json()
    assert upload_payload["feature_overlays"]
print("Web walkthrough assertions passed")
PY

kill "$SERVER_PID" >/dev/null 2>&1 || true
wait "$SERVER_PID" >/dev/null 2>&1 || true
SERVER_PID=""

echo "==> Building interactive explorer"
rm -rf interactive/node_modules interactive/.next interactive/out
npm --prefix interactive ci
npm --prefix interactive run build
npm --prefix interactive run lint
npm --prefix interactive run verify:export
git checkout -- interactive/next-env.d.ts interactive/tsconfig.tsbuildinfo >/dev/null 2>&1 || true

echo "==> Verifying repository hygiene"
if git ls-files .omx | grep -q .; then
  echo "Tracked .omx files detected" >&2
  exit 1
fi
if git ls-files | grep -E '(^|/)(IMPLEMENTATION|PLAN|SUMMARY|REVIEW|NOTES|REPORT|TODO)(-|$).*\.md$' >/dev/null; then
  echo "Tracked scratch markdown file detected" >&2
  exit 1
fi

echo "Walkthrough completed successfully. Artifacts: $ARTIFACT_DIR"
