from __future__ import annotations

import pytest
from textual.widgets import OptionList

from oci_vision.tui.app import CockpitConfig, VisionCockpitApp


@pytest.mark.asyncio
async def test_cockpit_boots_with_demo_defaults():
    app = VisionCockpitApp(CockpitConfig(demo=True))

    async with app.run_test(size=(160, 48)) as pilot:
        await pilot.pause()
        assert app.current_image == "dog_closeup.jpg"
        assert set(app.selected_features) == {"classification", "detection"}
        assert "Ready" in app.status_message


@pytest.mark.asyncio
async def test_gallery_selection_updates_recommended_features():
    app = VisionCockpitApp(CockpitConfig(demo=True))

    async with app.run_test(size=(160, 48)) as pilot:
        gallery = app.query_one("#gallery-list", OptionList)
        gallery.highlighted = 3
        gallery.action_select()
        await pilot.pause()

        assert app.current_image == "invoice_demo.png"
        assert app.selected_features == ["document"]


@pytest.mark.asyncio
async def test_string_feature_config_is_parsed_correctly():
    app = VisionCockpitApp(CockpitConfig(demo=True, features="classification,detection"))

    async with app.run_test(size=(160, 48)) as pilot:
        await pilot.pause()
        assert app.selected_features == ["classification", "detection"]


@pytest.mark.asyncio
async def test_analyze_action_populates_report_and_history():
    app = VisionCockpitApp(CockpitConfig(demo=True))

    async with app.run_test(size=(160, 48)) as pilot:
        await pilot.click("#analyze-button")
        await pilot.pause()

        assert app.current_report is not None
        assert app.current_report.classification is not None
        assert len(app.history) == 1
        assert "dog_closeup.jpg" in app.summary_text


@pytest.mark.asyncio
async def test_receipt_workflow_updates_workflow_panel():
    app = VisionCockpitApp(CockpitConfig(demo=True))

    async with app.run_test(size=(160, 48)) as pilot:
        gallery = app.query_one("#gallery-list", OptionList)
        gallery.highlighted = 3
        gallery.action_select()
        await pilot.pause()

        await pilot.click("#workflow-receipt-button")
        await pilot.pause()

        assert "Invoice Number" in app.workflow_output_text


@pytest.mark.asyncio
async def test_second_analysis_updates_compare_state():
    app = VisionCockpitApp(CockpitConfig(demo=True))

    async with app.run_test(size=(160, 48)) as pilot:
        await pilot.click("#analyze-button")
        await pilot.pause()

        gallery = app.query_one("#gallery-list", OptionList)
        gallery.highlighted = 3
        gallery.action_select()
        await pilot.pause()

        await pilot.click("#analyze-button")
        await pilot.pause()

        assert app.previous_report is not None
        assert app.previous_report.image_path == "dog_closeup.jpg"
        assert app.current_report is not None
        assert app.current_report.image_path == "invoice_demo.png"
        assert len(app.history) == 2
        assert "dog_closeup.jpg" in app.compare_text


@pytest.mark.asyncio
async def test_analyze_requires_at_least_one_feature():
    app = VisionCockpitApp(CockpitConfig(demo=True))

    async with app.run_test(size=(160, 48)) as pilot:
        await pilot.click("#feature-classification")
        await pilot.click("#feature-detection")
        await pilot.pause()

        await pilot.click("#analyze-button")
        await pilot.pause()

        assert app.current_report is None
        assert "Select at least one feature" in app.status_message
