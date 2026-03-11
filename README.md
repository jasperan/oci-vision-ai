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

- **CLI** (`oci-vision`) -- Rich-formatted terminal output, JSON, or HTML reports
- **Web Dashboard** -- FastAPI + drag-and-drop upload with toggleable feature overlays
- **Jupyter Notebooks** -- seven guided walkthroughs with inline visualisations

**Demo mode** -- cached real API responses, one `--demo` flag, works completely offline.

---

## Quick Start

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

Opens at **http://localhost:8000**. Drag and drop an image or pick one from the built-in gallery, toggle individual feature overlays, and inspect results in real time.

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

Demo mode serves cached responses recorded from the live OCI Vision API. It is enabled with a single boolean flag and requires no network access:

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

## Project Structure

```
src/oci_vision/
    __init__.py            # Public API re-exports (VisionClient, AnalysisReport)
    core/
        __init__.py        # Core re-exports
        client.py          # VisionClient -- unified demo/live API
        demo.py            # DemoClient -- offline cached responses
        models.py          # Pydantic v2 response models
        renderer.py        # Overlay image rendering (PIL/OpenCV)
    cli/
        __init__.py
        app.py             # Typer CLI application
        formatters.py      # Rich console output formatters
    gallery/
        __init__.py        # Gallery manifest loader
        manifest.json      # Curated demo image metadata
        images/            # Sample images
        responses/         # Cached OCI Vision API responses
    web/
        __init__.py        # Default FastAPI app instance
        app.py             # FastAPI web dashboard
        static/            # JavaScript and CSS
        templates/         # Jinja2 HTML templates
notebooks/                 # 7 guided Jupyter notebooks
tests/                     # pytest suite (98+ tests)
```

---

## License

[GPL-3.0](LICENSE)
