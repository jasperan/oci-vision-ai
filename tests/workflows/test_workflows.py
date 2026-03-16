from __future__ import annotations

from typer.testing import CliRunner

from oci_vision.cli.app import app
from oci_vision.core.client import VisionClient
from oci_vision.workflows.archive_search import archive_search_workflow
from oci_vision.workflows.inspection import inspection_workflow
from oci_vision.workflows.receipts import receipt_workflow
from oci_vision.workflows.shelf_audit import shelf_audit_workflow

runner = CliRunner()


def test_receipt_workflow_extracts_invoice_summary():
    client = VisionClient(demo=True)
    summary = receipt_workflow(client, "invoice_demo.png")

    assert summary["field_count"] >= 1
    assert summary["fields"]["Invoice Number"] == "INV-1001"


def test_shelf_audit_workflow_counts_objects():
    client = VisionClient(demo=True)
    summary = shelf_audit_workflow(client, "dog_closeup.jpg")

    assert summary["object_count"] >= 1
    assert summary["objects"]["Dog"] >= 1


def test_inspection_workflow_combines_multiple_features():
    client = VisionClient(demo=True)
    summary = inspection_workflow(client, "dog_closeup.jpg")

    assert "classification" in summary
    assert "detection" in summary


def test_archive_search_workflow_matches_query():
    client = VisionClient(demo=True)
    result = archive_search_workflow(client, ["invoice_demo.png"], query="INV-1001")

    assert result["matches"][0]["image"] == "invoice_demo.png"


def test_cli_workflow_receipt_demo():
    result = runner.invoke(app, ["workflow", "receipt", "invoice_demo.png", "--demo"])
    assert result.exit_code == 0
    assert "Invoice Number" in result.output
