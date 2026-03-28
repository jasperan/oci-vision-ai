from __future__ import annotations

from oci_vision import VisionClient
from oci_vision.core.insights import compare_reports, report_insights, summarize_batch, summarize_report


def test_summarize_report_extracts_key_counts():
    client = VisionClient(demo=True)
    report = client.analyze("dog_closeup.jpg")

    summary = summarize_report(report)

    assert summary["top_label"] == "Dog"
    assert summary["object_count"] >= 1
    assert "classification" in summary["features"]


def test_report_insights_returns_human_readable_lines():
    client = VisionClient(demo=True)
    report = client.analyze("invoice_demo.png")

    insights = report_insights(report)

    assert insights
    assert any("Document fields" in line for line in insights)


def test_compare_reports_highlights_feature_deltas():
    client = VisionClient(demo=True)
    left = client.analyze("dog_closeup.jpg")
    right = client.analyze("sign_board.png")

    comparison = compare_reports(left, right)

    assert "classification" in comparison["left_only_features"]
    assert "text" in comparison["right_only_features"]
    assert comparison["top_label_change"]["changed"] is True


def test_summarize_batch_aggregates_multiple_reports():
    client = VisionClient(demo=True)
    reports = [
        client.analyze("dog_closeup.jpg"),
        client.analyze("sign_board.png"),
        client.analyze("invoice_demo.png"),
    ]

    batch = summarize_batch(reports)

    assert batch["report_count"] == 3
    assert batch["feature_coverage"]["classification"] >= 1
    assert batch["reports"][0]["image"]
