from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    OptionList,
    Static,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

from oci_vision.core.client import VisionClient
from oci_vision.core.exports import save_overlay_image, write_html_report, write_json_report
from oci_vision.tui.insights import compare_reports, history_lines, push_history, summarize_report, summarize_workflow_result
from oci_vision.tui.services import (
    ALL_FEATURES,
    WORKFLOW_NAMES,
    derive_artifact_paths,
    find_gallery_entry,
    load_gallery_entries,
    parse_feature_selection,
    recommended_features_for_image,
    resolve_initial_image,
    run_analysis,
    run_named_workflow,
)


@dataclass(slots=True)
class CockpitConfig:
    demo: bool = False
    image: str | None = None
    features: Sequence[str] | str | None = None
    workflow: str | None = None
    query: str | None = None
    screenshot_path: str | None = None


class VisionCockpitApp(App[None]):
    CSS_PATH = str(Path(__file__).with_name("cockpit.tcss"))
    BINDINGS = [
        ("a", "analyze", "Analyze"),
        ("j", "export_json", "Export JSON"),
        ("h", "export_html", "Export HTML"),
        ("o", "export_overlay", "Export Overlay"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config: CockpitConfig | None = None):
        self.config = config or CockpitConfig()
        self.client = VisionClient(demo=self.config.demo)
        self.gallery_entries = load_gallery_entries()
        self.current_image = resolve_initial_image(self.config.image, demo=self.config.demo)
        self.current_report = None
        self.previous_report = None
        self.history: list = []
        self.workflow_output_text = "Pick a workflow to inspect a focused summary."
        self.compare_text = "Run another analysis to unlock compare mode."
        self.summary_text = "No analysis yet. Pick features and press Analyze."
        self.status_message = "Ready to analyze."
        self.artifact_paths: dict[str, Path] = {}
        self._feature_state = {feature: False for feature in ALL_FEATURES}
        self._pending_feature_override = (
            parse_feature_selection(self.config.features, default=[])
            if self.config.features
            else None
        )
        super().__init__()

    @property
    def selected_features(self) -> list[str]:
        return [feature for feature, enabled in self._feature_state.items() if enabled]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=not bool(self.config.screenshot_path))
        with Container(id="cockpit-root"):
            with Vertical(id="left-rail", classes="panel"):
                yield Static("OCI Vision AI\nDemo Cockpit", id="brand-block")
                yield Static("Gallery", classes="section-title")
                yield OptionList(
                    *(Option(entry.filename, id=entry.id) for entry in self.gallery_entries),
                    id="gallery-list",
                )
                yield Static("Workflow quick runs", classes="section-title")
                with Vertical(id="workflow-actions"):
                    yield Button("Receipt", id="workflow-receipt-button", classes="workflow-button")
                    yield Button("Shelf Audit", id="workflow-shelf-button", classes="workflow-button")
                    yield Button("Inspection", id="workflow-inspection-button", classes="workflow-button")
                    yield Button("Archive Search", id="workflow-archive-search-button", classes="workflow-button")
                yield Static("A analyze\nJ JSON\nH HTML\nO overlay\nQ quit", id="help-block")
            with Vertical(id="main-column"):
                yield Static(id="target-panel", classes="panel")
                with Horizontal(id="feature-row", classes="panel"):
                    yield Checkbox("Classification", id="feature-classification")
                    yield Checkbox("Detection", id="feature-detection")
                    yield Checkbox("OCR", id="feature-text")
                    yield Checkbox("Faces", id="feature-faces")
                    yield Checkbox("Document", id="feature-document")
                with Horizontal(id="action-row", classes="panel"):
                    yield Button("Analyze", id="analyze-button", variant="primary")
                    yield Button("Export JSON", id="export-json-button")
                    yield Button("Export HTML", id="export-html-button")
                    yield Button("Export Overlay", id="export-overlay-button")
                yield Static(id="summary-panel", classes="panel")
                with TabbedContent(id="results-tabs"):
                    with TabPane("Classification"):
                        yield Static(id="classification-output", classes="result-output")
                    with TabPane("Detection"):
                        yield Static(id="detection-output", classes="result-output")
                    with TabPane("OCR"):
                        yield Static(id="text-output", classes="result-output")
                    with TabPane("Faces"):
                        yield Static(id="faces-output", classes="result-output")
                    with TabPane("Document"):
                        yield Static(id="document-output", classes="result-output")
            with Vertical(id="right-rail"):
                with Vertical(classes="panel"):
                    yield Static("Archive query", classes="section-title")
                    yield Input(placeholder="INV-1001", id="archive-query")
                yield Static(id="workflow-panel", classes="panel")
                yield Static(id="compare-panel", classes="panel")
                yield Static(id="history-panel", classes="panel")
                yield Static(id="status-panel", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#archive-query", Input).value = self.config.query or ""
        self._select_image(self.current_image, update_gallery=True, use_recommended=True)
        if self._pending_feature_override:
            self._apply_feature_selection(self._pending_feature_override)
        self._refresh_all()
        if self.config.screenshot_path or self.config.workflow:
            self.set_timer(0.05, self._run_bootstrap_sequence)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "gallery-list":
            return
        option_id = event.option_id or self.gallery_entries[event.option_index].id
        entry = next((entry for entry in self.gallery_entries if entry.id == option_id), None)
        if entry is None:
            return
        self._select_image(entry.filename, update_gallery=False, use_recommended=True)
        self.status_message = f"Selected gallery image: {entry.filename}"
        self._refresh_all()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox_id = event.checkbox.id or ""
        if not checkbox_id.startswith("feature-"):
            return
        feature = checkbox_id.removeprefix("feature-")
        self._feature_state[feature] = event.value
        self._refresh_target_panel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "analyze-button":
            self.action_analyze()
            return
        if button_id == "export-json-button":
            self.action_export_json()
            return
        if button_id == "export-html-button":
            self.action_export_html()
            return
        if button_id == "export-overlay-button":
            self.action_export_overlay()
            return
        if button_id.startswith("workflow-") and button_id.endswith("-button"):
            workflow_name = button_id.removeprefix("workflow-").removesuffix("-button")
            self._run_workflow(workflow_name)

    def action_analyze(self) -> None:
        self._run_analysis()

    def action_export_json(self) -> None:
        self._export_current_report("json")

    def action_export_html(self) -> None:
        self._export_current_report("html")

    def action_export_overlay(self) -> None:
        self._export_current_report("overlay")

    def _run_bootstrap_sequence(self) -> None:
        self._run_analysis()
        if self.config.workflow:
            self._run_workflow(self.config.workflow)
        if self.config.screenshot_path:
            self.set_timer(0.1, self._capture_screenshot_and_exit)

    def _capture_screenshot_and_exit(self) -> None:
        screenshot_path = Path(self.config.screenshot_path or "cockpit.svg")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        saved = self.save_screenshot(filename=screenshot_path.name, path=str(screenshot_path.parent))
        if saved:
            _normalize_svg_screenshot(screenshot_path)
            self.status_message = f"Saved cockpit screenshot to {screenshot_path}"
        self._refresh_status_panel()
        self.exit()

    def _select_image(self, image: str, *, update_gallery: bool, use_recommended: bool) -> None:
        self.current_image = image
        entry = find_gallery_entry(image)
        if update_gallery and entry is not None:
            gallery = self.query_one("#gallery-list", OptionList)
            for index, gallery_entry in enumerate(self.gallery_entries):
                if gallery_entry.id == entry.id:
                    gallery.highlighted = index
                    break
        if use_recommended:
            self._apply_feature_selection(recommended_features_for_image(image))
        self._refresh_target_panel()

    def _apply_feature_selection(self, features: Sequence[str] | str) -> None:
        selected = parse_feature_selection(features, default=[])
        for feature in ALL_FEATURES:
            enabled = feature in selected
            self._feature_state[feature] = enabled
            checkbox = self.query_one(f"#feature-{feature}", Checkbox)
            checkbox.value = enabled
        self._refresh_target_panel()

    def _run_analysis(self) -> None:
        selected = self.selected_features
        if not selected:
            self.status_message = "Select at least one feature before running analysis."
            self._refresh_status_panel()
            return

        try:
            report = run_analysis(self.client, self.current_image, selected)
            if self.config.screenshot_path:
                report = report.model_copy(update={"elapsed_seconds": 0.0})
        except Exception as exc:  # pragma: no cover - defensive path
            self.status_message = f"Analysis failed: {exc}"
            self._refresh_status_panel()
            return

        if self.current_report is not None:
            self.previous_report = self.current_report
        self.current_report = report
        self.history = push_history(self.history, report, limit=5)

        summary = summarize_report(report)
        self.summary_text = (
            f"Image: {summary['image']}\n"
            f"Features: {', '.join(summary['features'])}\n"
            f"Top label: {summary['top_label']}\n"
            f"Objects: {summary['object_count']}\n"
            f"OCR lines: {summary['ocr_line_count']}\n"
            f"Faces: {summary['face_count']}\n"
            f"Doc fields: {summary['document_field_count']}\n"
            f"Elapsed: {summary['elapsed_seconds']:.3f}s"
        )

        compare = compare_reports(report, self.previous_report)
        self.compare_text = (
            f"{compare['summary']}\n"
            f"Top label: {compare['top_label_delta']}\n"
            f"Objects Δ: {compare['object_count_delta']}\n"
            f"OCR Δ: {compare['ocr_line_delta']}\n"
            f"Doc fields Δ: {compare['document_field_delta']}"
        )

        self.status_message = f"Analyzed {self.current_image} in {'demo' if self.config.demo else 'live'} mode."
        self._refresh_all()

    def _run_workflow(self, workflow_name: str) -> None:
        query = self.query_one("#archive-query", Input).value.strip() or None
        try:
            result = run_named_workflow(self.client, workflow_name, self.current_image, query=query)
        except Exception as exc:
            self.status_message = str(exc)
            self._refresh_status_panel()
            return

        self.workflow_output_text = summarize_workflow_result(workflow_name, result)
        self.status_message = f"Ran {workflow_name} workflow for {self.current_image}."
        self._refresh_workflow_panel()
        self._refresh_status_panel()

    def _export_current_report(self, artifact_type: str) -> None:
        if self.current_report is None:
            self.status_message = "Run an analysis before exporting artifacts."
            self._refresh_status_panel()
            return

        paths = derive_artifact_paths(self.current_report.image_path)
        try:
            if artifact_type == "json":
                path = write_json_report(self.current_report, paths["json"])
            elif artifact_type == "html":
                path = write_html_report(self.current_report, paths["html"])
            elif artifact_type == "overlay":
                path = save_overlay_image(self.current_report, self.current_image, paths["overlay"])
            else:  # pragma: no cover - defensive path
                raise ValueError(f"Unsupported export type: {artifact_type}")
        except Exception as exc:
            self.status_message = f"Export failed: {exc}"
            self._refresh_status_panel()
            return

        self.artifact_paths[artifact_type] = path
        self.status_message = f"Exported {artifact_type} artifact to {path}"
        self._refresh_status_panel()

    def _refresh_all(self) -> None:
        self._refresh_target_panel()
        self._refresh_summary_panel()
        self._refresh_result_tabs()
        self._refresh_workflow_panel()
        self._refresh_compare_panel()
        self._refresh_history_panel()
        self._refresh_status_panel()

    def _refresh_target_panel(self) -> None:
        mode = "Demo" if self.config.demo else "Live"
        self.query_one("#target-panel", Static).update(
            f"Mode: {mode}\n"
            f"Target: {self.current_image}\n"
            f"Selected features: {', '.join(self.selected_features) or 'none'}"
        )

    def _refresh_summary_panel(self) -> None:
        self.query_one("#summary-panel", Static).update(self.summary_text)

    def _refresh_result_tabs(self) -> None:
        self.query_one("#classification-output", Static).update(self._classification_text())
        self.query_one("#detection-output", Static).update(self._detection_text())
        self.query_one("#text-output", Static).update(self._text_text())
        self.query_one("#faces-output", Static).update(self._faces_text())
        self.query_one("#document-output", Static).update(self._document_text())

    def _refresh_workflow_panel(self) -> None:
        self.query_one("#workflow-panel", Static).update(self.workflow_output_text)

    def _refresh_compare_panel(self) -> None:
        self.query_one("#compare-panel", Static).update(self.compare_text)

    def _refresh_history_panel(self) -> None:
        lines = history_lines(self.history)
        content = "Recent runs\n" + ("\n".join(lines) if lines else "No runs yet.")
        self.query_one("#history-panel", Static).update(content)

    def _refresh_status_panel(self) -> None:
        artifact_lines = [f"- {kind}: {path}" for kind, path in sorted(self.artifact_paths.items())]
        suffix = "\nArtifacts\n" + "\n".join(artifact_lines) if artifact_lines else ""
        self.query_one("#status-panel", Static).update(self.status_message + suffix)

    def _classification_text(self) -> str:
        if self.current_report is None or self.current_report.classification is None:
            return "No classification result yet."
        return "\n".join(
            ["Classification"]
            + [f"- {label.name}: {label.confidence_pct:.1f}%" for label in self.current_report.classification.labels[:10]]
        )

    def _detection_text(self) -> str:
        if self.current_report is None or self.current_report.detection is None:
            return "No detection result yet."
        lines = ["Detection"]
        for detected in self.current_report.detection.objects[:10]:
            position = detected.bounding_polygon.human_position(1.0, 1.0)
            lines.append(f"- {detected.name}: {detected.confidence_pct:.1f}% ({position})")
        return "\n".join(lines)

    def _text_text(self) -> str:
        if self.current_report is None or self.current_report.text is None:
            return "No OCR result yet."
        lines = ["OCR"] + [f"- {line.text}" for line in self.current_report.text.lines[:12]]
        return "\n".join(lines)

    def _faces_text(self) -> str:
        if self.current_report is None or self.current_report.faces is None:
            return "No face result yet."
        lines = [f"Faces detected: {len(self.current_report.faces.faces)}"]
        for index, face in enumerate(self.current_report.faces.faces[:5], start=1):
            lines.append(f"- Face {index}: {round(face.confidence * 100, 1)}% with {len(face.landmarks)} landmarks")
        return "\n".join(lines)

    def _document_text(self) -> str:
        if self.current_report is None or self.current_report.document is None:
            return "No document result yet."
        lines = [
            f"Fields: {len(self.current_report.document.fields)}",
            f"Tables: {len(self.current_report.document.tables)}",
        ]
        for field in self.current_report.document.fields[:8]:
            lines.append(f"- {field.label}: {field.value}")
        return "\n".join(lines)


async def _capture_with_headless_test(config: CockpitConfig) -> Path:
    app = VisionCockpitApp(config)
    async with app.run_test(size=(160, 48)) as pilot:
        await pilot.pause(0.6)
    path = Path(config.screenshot_path or "cockpit.svg")
    if not path.exists():
        raise RuntimeError(f"Cockpit screenshot was not created: {path}")
    return path


def capture_cockpit_screenshot(config: CockpitConfig) -> Path:
    return asyncio.run(_capture_with_headless_test(config))


def _normalize_svg_screenshot(path: Path) -> None:
    if path.suffix.lower() != ".svg" or not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    normalized = re.sub(r"terminal-\d+", "terminal-cockpit", content)
    path.write_text(normalized, encoding="utf-8")
