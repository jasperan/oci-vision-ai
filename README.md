# OCI Vision AI

The definitive Oracle Cloud Infrastructure Vision AI showcase.

Analyse images with six OCI Vision features through a polished CLI, an interactive web dashboard, or hands-on Jupyter notebooks -- all runnable offline in demo mode with zero cloud credentials.

---

## Features

**Vision capabilities**

- **Image Classification** -- label images with confidence scores
- **Object Detection** -- locate objects with bounding polygons
- **Text / OCR** -- extract printed and handwritten text
- **Face Detection** -- find faces and facial landmarks
- **Document AI** -- extract fields and tables from invoices, receipts, and forms
- **Custom Models** -- bring your own OCI Vision model

**Delivery surfaces**

- **CLI** (`oci-vision`) -- Rich-formatted terminal output, JSON, HTML reports, eval commands, workflow packs, and demo recording
- **Web Dashboard** -- FastAPI + drag-and-drop upload with toggleable feature overlays, compare page, API playground, and report pages
- **Jupyter Notebooks** -- seven guided walkthroughs with inline visualisations

**Platform extras**

- **Evaluation Lab** -- detection metrics, OCR similarity, and document diffing
- **Workflow Packs** -- receipt intake, shelf audit, inspection, and archive search
- **Oracle Database 26ai Integration** -- optional run storage and semantic search with local Oracle Database Free

**Demo mode** -- fixture-backed cached responses, one `--demo` flag, works completely offline.

---

## Quick Start

<!-- one-command-install -->
> **One-command install** — clone, configure, and run in a single step:
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/jasperan/oci-vision-ai/main/install.sh | bash
> ```
>
> <details><summary>Advanced options</summary>
>
> Override install location:
> ```bash
> PROJECT_DIR=/opt/myapp curl -fsSL https://raw.githubusercontent.com/jasperan/oci-vision-ai/main/install.sh | bash
> ```
>
> Or install manually:
> ```bash
> git clone https://github.com/jasperan/oci-vision-ai.git
> cd oci-vision-ai
> # See below for setup instructions
> ```
> </details>


```bash
pip install -e ".[all]"
oci-vision analyze dog_closeup.jpg --demo
oci-vision web --demo
```

---

## CLI Usage

Every command accepts `--demo` to run without OCI credentials.

```bash
# Full analysis (all features)
oci-vision analyze photo.jpg --demo

# Individual features
oci-vision classify photo.jpg --demo
oci-vision detect photo.jpg --demo
oci-vision ocr document.pdf --demo
oci-vision faces group.jpg --demo
oci-vision document invoice.pdf --demo

# Browse the demo gallery
oci-vision gallery

# Evaluation lab
oci-vision eval detection pred.json truth.json --output-format json

# Workflow packs
oci-vision workflow receipt invoice_demo.png --demo
oci-vision workflow shelf dog_closeup.jpg --demo

# Record a new fixture into the demo gallery
oci-vision record-demo ./sample.png --feature text --response-json ./response.json

# Optional Oracle-backed semantic search
oci-vision search-runs "invoice number"

# JSON output
oci-vision analyze photo.jpg --demo --output-format json

# Save annotated overlay image
oci-vision analyze photo.jpg --demo --save-overlay annotated.png
```

Run `oci-vision --help` for the full option reference.

---

## Web Dashboard

```bash
oci-vision web --demo
```

Opens at **http://localhost:8000**. Drag and drop an image or pick one from the built-in gallery, toggle feature-specific overlays, inspect normalized JSON in the API playground, open shareable report pages, and use the compare surface for side-by-side review.

---

## Notebooks

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_quickstart.ipynb` | End-to-end walkthrough -- classify, detect, OCR in one notebook |
| 02 | `02_classification.ipynb` | Deep dive into image classification with threshold tuning |
| 03 | `03_object_detection.ipynb` | Object detection, bounding boxes, and overlay rendering |
| 04 | `04_ocr.ipynb` | Text extraction from photos and scanned documents |
| 05 | `05_face_detection.ipynb` | Face detection with landmark visualisation |
| 06 | `06_document_ai.ipynb` | Document AI -- field and table extraction |
| 07 | `07_custom_models.ipynb` | Bring-your-own-model workflow on OCI Vision |

All notebooks run in demo mode by default -- no OCI credentials needed.

```bash
pip install -e ".[notebooks]"
jupyter notebook notebooks/
```

---

## Demo Mode

Demo mode serves fixture-backed cached responses that match the OCI Vision response shapes. Fixtures can be recorded into the gallery with `oci-vision record-demo ...`. Demo mode is enabled with a single boolean flag and requires no network access:

```python
from oci_vision import VisionClient

client = VisionClient(demo=True)
report = client.analyze("dog_closeup.jpg")
print(report.available_features)  # ['classification', 'detection', ...]
```

On the CLI, pass `--demo`. In the web dashboard, pass `--demo` to the `web` command. Notebooks default to demo mode.

---

## Live Mode (OCI Credentials)

To call the real OCI Vision service, configure an API key following the [OCI SDK setup guide](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm), then:

```python
from oci_vision import VisionClient

client = VisionClient()                          # uses ~/.oci/config
report = client.analyze("oci://my-bucket/photo.jpg")

# Or from a local file
report = client.analyze("/path/to/photo.jpg")
```

---

## Python API

```python
from oci_vision import VisionClient, AnalysisReport

client = VisionClient(demo=True)

# Full analysis
report: AnalysisReport = client.analyze("photo.jpg")

# Individual features
classification = client.classify("photo.jpg")
detection      = client.detect_objects("photo.jpg")
text           = client.detect_text("photo.jpg")
faces          = client.detect_faces("photo.jpg")
document       = client.analyze_document("invoice.pdf")

# Selective features
report = client.analyze("photo.jpg", features=["classification", "detection"])
```

Key model classes: `AnalysisReport`, `ClassificationResult`, `DetectionResult`, `TextDetectionResult`, `FaceDetectionResult`, `DocumentResult`.

---

## Oracle Database 26ai Free

Oracle-backed storage is optional and off by default.

Start the local Oracle Database Free container:

```bash
docker compose -f docker-compose.oracle.yml up -d
```

Enable Oracle integration for the current shell:

```bash
export OCI_VISION_ENABLE_ORACLE=1
export OCI_VISION_ORACLE_USER=system
export OCI_VISION_ORACLE_PASSWORD=VisionAI2026
export OCI_VISION_ORACLE_HOST=localhost
export OCI_VISION_ORACLE_PORT=1524
export OCI_VISION_ORACLE_SERVICE=FREEPDB1
```

Then analyses can be stored automatically and searched from the CLI:

```bash
oci-vision analyze invoice_demo.png --demo
oci-vision search-runs "INV-1001"
```

---

## Project Structure

```
src/oci_vision/
    __init__.py            # Public API re-exports (VisionClient, AnalysisReport)
    core/
        __init__.py        # Core re-exports
        client.py          # VisionClient -- unified demo/live API
        demo.py            # DemoClient -- offline cached responses
        models.py          # Pydantic v2 response models
        recording.py       # Demo fixture recording helpers
        renderer.py        # Overlay image rendering (PIL/OpenCV)
    cli/
        __init__.py
        app.py             # Typer CLI application
        formatters.py      # Rich console output formatters
    eval/
        detection.py       # IoU / precision / recall helpers
        text.py            # OCR similarity helpers
        document.py        # Document field/table diffing
        reports.py         # HTML evaluation reports
    gallery/
        __init__.py        # Gallery manifest loader
        manifest.json      # Curated demo image metadata
        images/            # Sample images
        responses/         # Cached OCI Vision API responses
    oracle/
        config.py          # Optional Oracle env/config loader
        connection.py      # python-oracledb connection helper
        schema.py          # Oracle 26ai schema bootstrap
        store.py           # Run ingest + vector search helpers
    web/
        __init__.py        # Default FastAPI app instance
        app.py             # FastAPI web dashboard
        static/            # JavaScript and CSS
        templates/         # Jinja2 HTML templates
    workflows/
        receipts.py        # Receipt / invoice workflow pack
        shelf_audit.py     # Shelf-audit workflow pack
        inspection.py      # Inspection workflow pack
        archive_search.py  # Archive-search workflow pack
notebooks/                 # 7 guided Jupyter notebooks
tests/                     # pytest suite (130+ tests)
```

---

## License

[GPL-3.0](LICENSE)
