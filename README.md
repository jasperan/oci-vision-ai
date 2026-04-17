<p align="center">
  <img src="docs/slides/slide-01.png" alt="OCI Vision AI" width="600"/>
</p>

<h1 align="center">OCI Vision AI</h1>

<p align="center"><strong>Classify images. Detect objects. Extract text. Find faces. Parse documents. All from one unified client.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/OCI-Vision_API-red?style=for-the-badge&logo=oracle&logoColor=white" alt="OCI"/>
  <img src="https://img.shields.io/badge/FastAPI-Dashboard-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Pydantic-v2-e92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic"/>
  <img src="https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <a href="https://github.com/jasperan/oci-vision-ai/actions/workflows/build-install-smoke.yml"><img src="https://github.com/jasperan/oci-vision-ai/actions/workflows/build-install-smoke.yml/badge.svg" alt="build-install-smoke"/></a>
  <a href="https://github.com/jasperan/oci-vision-ai/actions/workflows/dependency-audit.yml"><img src="https://github.com/jasperan/oci-vision-ai/actions/workflows/dependency-audit.yml/badge.svg" alt="dependency-audit"/></a>
</p>

---

The definitive Oracle Cloud Infrastructure Vision AI showcase. Analyse images with six OCI Vision features through a polished CLI, an interactive web dashboard, or hands-on Jupyter notebooks. **Demo mode runs without OCI credentials** and stays offline-friendly across every surface.

Every chapter ships runnable commands, interactive notebooks, and a live web dashboard.

## Architecture at a Glance

<table>
  <tr>
    <td align="center"><strong>Title</strong><br><img src="docs/slides/slide-01.png" alt="Title" width="400"/></td>
    <td align="center"><strong>Architecture</strong><br><img src="docs/slides/slide-03.png" alt="Architecture" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><strong>Features</strong><br><img src="docs/slides/slide-04.png" alt="Features" width="400"/></td>
    <td align="center"><strong>Tech Stack</strong><br><img src="docs/slides/slide-05.png" alt="Tech Stack" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><strong>Overview</strong><br><img src="docs/slides/slide-02.png" alt="Overview" width="400"/></td>
    <td align="center"><strong>Getting Started</strong><br><img src="docs/slides/slide-06.png" alt="Getting Started" width="400"/></td>
  </tr>
</table>

<p align="center">
  <a href="docs/slides/presentation.html">View the full interactive presentation &rarr;</a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="interactive/">Explore the Interactive Textbook &rarr;</a>
</p>

## Vision Capabilities

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Image Classification** | Label images with confidence scores |
| 2 | **Object Detection** | Locate objects with bounding polygons |
| 3 | **Text / OCR** | Extract printed and handwritten text |
| 4 | **Face Detection** | Find faces and facial landmarks |
| 5 | **Document AI** | Extract fields and tables from invoices, receipts, and forms |
| 6 | **Custom Models** | Bring your own OCI Vision model |

### Interactive Explorer

The `interactive/` directory contains a **learn-by-play** interactive textbook built with Next.js, React 19, and Tailwind CSS. It features 8 hands-on widgets across all 8 sections -- drag confidence thresholds, hover bounding boxes, step through OCR pipelines, toggle face landmarks, explore Document AI extraction, calculate IoU metrics, toggle demo/live architecture, and animate workflow packs.

```bash
cd interactive && npm ci && npm run dev
```

For a production-style verification run:

```bash
cd interactive && npm ci && npm run build && npm run lint && npm run verify:export
```

See [`interactive/README.md`](interactive/README.md) for the focused explorer workflow.

## Quick Start

> ```bash
> curl -fsSL https://raw.githubusercontent.com/jasperan/oci-vision-ai/main/install.sh | bash
> ```

<details>
<summary>Advanced: manual setup</summary>

```bash
git clone https://github.com/jasperan/oci-vision-ai.git
cd oci-vision-ai
pip install -e .
```

</details>

### Run in demo mode (no OCI credentials needed)

```bash
oci-vision analyze dog_closeup.jpg --demo
oci-vision compare dog_closeup.jpg sign_board.png --demo --output-format json
oci-vision batch dog_closeup.jpg sign_board.png invoice_demo.png --demo --output-format json
oci-vision showcase --demo --output-dir showcase
oci-vision cockpit --demo
oci-vision web --demo
```

### Generate a portable demo bundle

If you want one command that proves the shipped demo assets and workflows are healthy, generate a showcase bundle:

```bash
oci-vision showcase --demo --output-dir showcase
```

That directory will contain per-image JSON/HTML reports, overlay images, workflow summaries, a batch summary, and an `index.html` entry point.

### Install options

- `pip install -e .` -- demo CLI, cockpit, and web dashboard
- `pip install -e ".[live]"` -- add OCI SDK for live mode
- `pip install -e ".[notebooks]"` -- add notebook tooling
- `pip install -e ".[all]"` -- everything

## Full README Walkthrough

To exercise the project the way a hands-on reader would -- install it, run the CLI, capture the TUI, hit the web API, and build the interactive app -- use:

```bash
bash scripts/readme_walkthrough.sh
```

The script also checks that `.omx/` state and common agent scratch markdown files are not tracked by git.

## Delivery Surfaces

| Surface | Command | What You Get |
|---------|---------|-------------|
| **CLI** | `oci-vision analyze img.jpg --demo` | Rich-formatted terminal output, JSON/HTML reports |
| **TUI Cockpit** | `oci-vision cockpit --demo` | Gallery browsing, feature toggles, workflow launchers |
| **Web Dashboard** | `oci-vision web --demo` | FastAPI + drag-and-drop upload, toggleable overlays |
| **Notebooks** | `jupyter notebook notebooks/` | 7 guided walkthroughs with inline visualisations |

## Notebooks

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_quickstart.ipynb` | End-to-end walkthrough -- classify, detect, OCR in one notebook |
| 02 | `02_classification.ipynb` | Image classification with threshold tuning |
| 03 | `03_object_detection.ipynb` | Object detection, bounding boxes, and overlay rendering |
| 04 | `04_ocr.ipynb` | Text extraction from photos and scanned documents |
| 05 | `05_face_detection.ipynb` | Face detection with landmark visualisation |
| 06 | `06_document_ai.ipynb` | Document AI -- field and table extraction |
| 07 | `07_custom_models.ipynb` | Bring-your-own-model workflow on OCI Vision |

All notebooks run in demo mode by default -- no OCI credentials needed.

## Textual Demo Cockpit

The cockpit is a polished terminal control room for the project. It gives you gallery browsing, feature toggles, workflow launchers, run history, lightweight compare mode, and export actions in one screen.

```bash
oci-vision cockpit --demo
```

**Overview**

![OCI Vision AI cockpit overview](https://raw.githubusercontent.com/jasperan/oci-vision-ai/main/docs/images/tui-cockpit-overview.png)

**Workflow panel**

![OCI Vision AI cockpit workflow view](https://raw.githubusercontent.com/jasperan/oci-vision-ai/main/docs/images/tui-cockpit-workflow.png)

## Demo Mode

Demo mode serves fixture-backed cached responses that match the OCI Vision response shapes. Fixtures can be recorded into the gallery with `oci-vision record-demo`. Enabled with a single `--demo` flag.

**Bundled fixtures:** `dog_closeup.jpg`, `sign_board.png`, `portrait_demo.png`, `invoice_demo.png`

```python
from oci_vision import VisionClient

client = VisionClient(demo=True)
report = client.analyze("dog_closeup.jpg")
print(report.available_features)  # ['classification', 'detection', ...]
```

## Python API

```python
from oci_vision import VisionClient, AnalysisReport

client = VisionClient(demo=True)

# Full analysis
report: AnalysisReport = client.analyze("dog_closeup.jpg")

# Individual features
classification = client.classify("dog_closeup.jpg")
detection      = client.detect_objects("dog_closeup.jpg")
text           = client.detect_text("sign_board.png")
faces          = client.detect_faces("portrait_demo.png")
document       = client.analyze_document("invoice_demo.png")

# Selective features
report = client.analyze("dog_closeup.jpg", features=["classification", "detection"])
```

## Evaluation Lab

The project ships with standard ML metrics:

- **Detection:** IoU (Intersection over Union), precision/recall/F1, threshold sweep
- **OCR:** Normalized edit distance, text similarity, line accuracy
- **Document AI:** Field and table diffing

```bash
oci-vision eval detection pred.json truth.json --output-format json
```

## Workflow Packs

Four production-ready workflow packs that chain multiple vision features:

| Workflow | Features Used | CLI Command |
|----------|--------------|-------------|
| **Receipt Intake** | Document AI | `oci-vision workflow receipt invoice.png --demo` |
| **Shelf Audit** | Object Detection | `oci-vision workflow shelf dog_closeup.jpg --demo` |
| **Inspection** | Classification + Detection + OCR | `oci-vision workflow inspection img.jpg --demo` |
| **Archive Search** | OCR + Document AI | `oci-vision workflow archive-search "keyword"` |

## Oracle Database 26ai Free

Optional Oracle-backed run storage and semantic search:

```bash
pip install -e ".[oracle]"
docker compose -f docker-compose.oracle.yml up -d
export OCI_VISION_ENABLE_ORACLE=1
oci-vision analyze invoice_demo.png --demo
oci-vision search-runs "INV-1001"
```

Oracle port: **1524** (not standard 1521).

## CI and Security

- [`build-install-smoke`](https://github.com/jasperan/oci-vision-ai/actions/workflows/build-install-smoke.yml) -- package build, install flow, demo CLI paths, compare/batch commands, cockpit screenshot, web assets
- [`dependency-audit`](https://github.com/jasperan/oci-vision-ai/actions/workflows/dependency-audit.yml) -- audits the base install path and uploads a markdown report artifact

## Project Structure

```
src/oci_vision/
    core/
        client.py          # VisionClient -- unified demo/live API
        demo.py            # DemoClient -- offline cached responses
        models.py          # Pydantic v2 response models
        insights.py        # Summaries, compare logic, batch aggregation
        renderer.py        # Overlay image rendering (PIL)
    cli/
        app.py             # Typer CLI application
        formatters.py      # Rich console output formatters
    tui/
        app.py             # Textual demo cockpit
    eval/
        detection.py       # IoU / precision / recall
        text.py            # OCR similarity
        document.py        # Document field/table diffing
    gallery/
        manifest.json      # Curated demo image metadata
        images/            # Sample images
        responses/         # Cached OCI Vision API responses
    oracle/                # Optional Oracle 26ai integration
    web/
        app.py             # FastAPI web dashboard
    workflows/             # Receipt, shelf audit, inspection, archive search
notebooks/                 # 7 guided Jupyter notebooks
interactive/               # Learn-by-play interactive textbook (8 widgets)
tests/                     # pytest suite (200+ tests)
```

## License

[GPL-3.0](LICENSE)

---

<div align="center">
  <a href="https://github.com/jasperan"><img src="https://img.shields.io/badge/GitHub-jasperan-181717?style=for-the-badge&logo=github" alt="GitHub"/></a>
  &nbsp;
  <a href="https://linkedin.com/in/jasperan"><img src="https://img.shields.io/badge/LinkedIn-jasperan-0A66C2?style=for-the-badge&logo=linkedin" alt="LinkedIn"/></a>
</div>
