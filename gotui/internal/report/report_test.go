package report

import "testing"

// The fixtures below are trimmed copies of real `oci-vision ... --output-format
// json` output. Field names are the contract between this front-end and the
// Python models, so they are asserted rather than assumed.

const analysisJSON = `{
  "image_path": "dog_closeup.jpg",
  "classification": {
    "model_version": "1.5.97",
    "labels": [
      {"name": "Dog", "confidence": 0.9925129, "confidence_pct": 99.25},
      {"name": "Vegetation", "confidence": 0.9876839, "confidence_pct": 98.77}
    ]
  },
  "detection": {
    "model_version": "1.3.557",
    "objects": [
      {
        "name": "Dog",
        "confidence": 0.98203605,
        "bounding_polygon": {
          "normalized_vertices": [{"x": 0.32, "y": 0.37}],
          "center": [0.39111328125, 0.5017361111111112]
        },
        "confidence_pct": 98.2
      }
    ]
  },
  "text": null,
  "faces": null,
  "document": null,
  "elapsed_seconds": 0.001,
  "available_features": ["classification", "detection"],
  "insights": ["Top label: Dog (99.2%)"]
}`

func TestDecodeAnalysis(t *testing.T) {
	analysis, err := Decode[Analysis]([]byte(analysisJSON))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}

	if analysis.ImagePath != "dog_closeup.jpg" {
		t.Errorf("ImagePath = %q", analysis.ImagePath)
	}
	if analysis.Classification == nil || len(analysis.Classification.Labels) != 2 {
		t.Fatalf("classification not decoded: %+v", analysis.Classification)
	}
	if got := analysis.Classification.Labels[0].ConfidencePct; got != 99.25 {
		t.Errorf("first label confidence_pct = %v, want 99.25", got)
	}
	if analysis.Detection == nil || len(analysis.Detection.Objects) != 1 {
		t.Fatalf("detection not decoded: %+v", analysis.Detection)
	}
	if got := len(analysis.Detection.Objects[0].BoundingPolygon.Center); got != 2 {
		t.Errorf("bounding polygon center has %d values, want 2", got)
	}
	// A feature the image does not support must stay nil, not decode to an empty
	// struct: the UI uses nil to decide which panes to draw.
	if analysis.Text != nil || analysis.Faces != nil || analysis.Document != nil {
		t.Errorf("absent features decoded as non-nil: text=%v faces=%v document=%v",
			analysis.Text, analysis.Faces, analysis.Document)
	}
	if len(analysis.Insights) != 1 {
		t.Errorf("insights = %v", analysis.Insights)
	}
	if len(analysis.AvailableFeatures) != 2 {
		t.Errorf("available_features = %v", analysis.AvailableFeatures)
	}
}

const documentJSON = `{
  "image_path": "invoice_demo.png",
  "document": {
    "model_version": "1.0",
    "fields": [
      {"field_type": "KEY_VALUE", "label": "Invoice Number", "value": "INV-1001", "confidence": 0.97}
    ],
    "tables": [
      {
        "row_count": 2,
        "column_count": 3,
        "header_rows": ["Item", "Qty", "Price"],
        "body_rows": [["Widget", "2", "$10.00"]],
        "confidence": 0.96
      }
    ],
    "full_text": "INV-1001",
    "page_count": 1
  },
  "available_features": ["document"],
  "insights": ["Document fields: 2, tables: 1"]
}`

func TestDecodeDocumentResult(t *testing.T) {
	analysis, err := Decode[Analysis]([]byte(documentJSON))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	if analysis.Document == nil {
		t.Fatal("document result not decoded")
	}
	if analysis.Document.PageCount != 1 {
		t.Errorf("PageCount = %d", analysis.Document.PageCount)
	}
	if len(analysis.Document.Fields) != 1 || analysis.Document.Fields[0].Value != "INV-1001" {
		t.Errorf("fields = %+v", analysis.Document.Fields)
	}
	if len(analysis.Document.Tables) != 1 {
		t.Fatalf("tables = %+v", analysis.Document.Tables)
	}
	table := analysis.Document.Tables[0]
	if len(table.HeaderRows) != 3 || len(table.BodyRows) != 1 || len(table.BodyRows[0]) != 3 {
		t.Errorf("table shape = headers %v body %v", table.HeaderRows, table.BodyRows)
	}
}

// TestDecodeTextAndFaces covers the two shapes whose nested lists matter for
// rendering (OCR words and face landmarks).
func TestDecodeTextAndFaces(t *testing.T) {
	textJSON := `{
      "image_path": "sign_board.png",
      "text": {
        "model_version": "1.0",
        "lines": [{"text": "STOP", "confidence": 0.99,
          "bounding_polygon": {"normalized_vertices": [], "center": [0.32, 0.21]},
          "words": [{"text": "STOP", "confidence": 0.99,
            "bounding_polygon": {"normalized_vertices": [], "center": [0.32, 0.21]}}]}],
        "full_text": "STOP\nSCHOOL XING"
      },
      "available_features": ["text"], "insights": ["OCR extracted 2 line(s)"]}`

	analysis, err := Decode[Analysis]([]byte(textJSON))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	if analysis.Text == nil || len(analysis.Text.Lines) != 1 {
		t.Fatalf("text not decoded: %+v", analysis.Text)
	}
	if got := len(analysis.Text.Lines[0].Words); got != 1 {
		t.Errorf("words = %d, want 1", got)
	}
	if analysis.Text.FullText != "STOP\nSCHOOL XING" {
		t.Errorf("full_text = %q", analysis.Text.FullText)
	}

	facesJSON := `{
      "image_path": "portrait_demo.png",
      "faces": {
        "model_version": "1.0",
        "faces": [{
          "confidence": 0.98,
          "bounding_polygon": {"normalized_vertices": [], "center": [0.5, 0.5]},
          "landmarks": [
            {"type": "LEFT_EYE", "x": 0.42, "y": 0.4},
            {"type": "RIGHT_EYE", "x": 0.58, "y": 0.4}
          ]
        }]
      },
      "available_features": ["faces"], "insights": ["Found 1 face(s)"]}`

	analysis, err = Decode[Analysis]([]byte(facesJSON))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	if analysis.Faces == nil || len(analysis.Faces.Faces) != 1 {
		t.Fatalf("faces not decoded: %+v", analysis.Faces)
	}
	if got := analysis.Faces.Faces[0].Landmarks; len(got) != 2 || got[0].Type != "LEFT_EYE" {
		t.Errorf("landmarks = %+v", got)
	}
}

func TestDecodeComparison(t *testing.T) {
	const comparisonJSON = `{
      "left_image": "dog_closeup.jpg",
      "right_image": "sign_board.png",
      "shared_features": [],
      "left_only_features": ["classification", "detection"],
      "right_only_features": ["text"],
      "top_label_change": {"left": "Dog", "right": "\u2014", "changed": true},
      "object_count_delta": -11,
      "object_deltas": [{"name": "Dog", "left": 5, "right": 0, "delta": -5}],
      "ocr_similarity": null,
      "ocr_line_delta": 2,
      "face_count_delta": 0,
      "document_field_delta": 0,
      "document_field_changes": [
        {"label": "Total Due", "left": "$10.00", "right": null, "changed": true}
      ],
      "left_summary": {"image": "dog_closeup.jpg", "features": ["detection"], "feature_count": 1,
        "top_label": "Dog", "top_confidence_pct": 99.25, "object_count": 11,
        "object_counts": {"Dog": 5}, "ocr_line_count": 0, "ocr_preview": "",
        "face_count": 0, "document_field_count": 0, "document_fields": {},
        "document_table_count": 0, "elapsed_seconds": 0.001},
      "right_summary": {"image": "sign_board.png", "features": ["text"], "feature_count": 1,
        "top_label": "\u2014", "top_confidence_pct": null, "object_count": 0,
        "object_counts": {}, "ocr_line_count": 2, "ocr_preview": "STOP",
        "face_count": 0, "document_field_count": 0, "document_fields": {},
        "document_table_count": 0, "elapsed_seconds": 0.0}
    }`

	comparison, err := Decode[Comparison]([]byte(comparisonJSON))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	if comparison.ObjectCountDelta != -11 {
		t.Errorf("ObjectCountDelta = %d", comparison.ObjectCountDelta)
	}
	if len(comparison.ObjectDeltas) != 1 || comparison.ObjectDeltas[0].Delta != -5 {
		t.Errorf("ObjectDeltas = %+v", comparison.ObjectDeltas)
	}
	// A documented negative delta must survive as negative, not be read as |delta|.
	if !comparison.TopLabelChange.Changed {
		t.Error("TopLabelChange.Changed = false, want true")
	}
	// A null similarity must stay nil so the UI omits the row instead of showing 0.
	if comparison.OCRSimilarity != nil {
		t.Errorf("OCRSimilarity = %v, want nil", *comparison.OCRSimilarity)
	}
	// A null top confidence must stay nil.
	if comparison.RightSummary.TopConfidencePct != nil {
		t.Errorf("right top confidence = %v, want nil", *comparison.RightSummary.TopConfidencePct)
	}
	if len(comparison.DocumentFieldChanges) != 1 {
		t.Fatalf("DocumentFieldChanges = %+v", comparison.DocumentFieldChanges)
	}
	change := comparison.DocumentFieldChanges[0]
	if change.Left == nil || *change.Left != "$10.00" {
		t.Errorf("change.Left = %v", change.Left)
	}
	if change.Right != nil {
		t.Errorf("change.Right = %v, want nil", *change.Right)
	}
}

func TestDecodeShowcase(t *testing.T) {
	const showcaseJSON = `{
      "generated_at": "2026-09-15T10:14:07.338322+00:00",
      "demo": true,
      "asset_count": 4,
      "workflow_count": 4,
      "comparison_count": 2,
      "gallery": [{
        "id": "dog_closeup", "filename": "dog_closeup.jpg", "description": "A dog",
        "recommended_features": ["classification"], "command": "oci-vision analyze dog_closeup.jpg --demo",
        "summary": {"image": "dog_closeup.jpg", "features": ["classification"], "feature_count": 1,
          "top_label": "Dog", "top_confidence_pct": 99.25, "object_count": 11,
          "object_counts": {"Dog": 5}, "ocr_line_count": 0, "ocr_preview": "",
          "face_count": 0, "document_field_count": 0, "document_fields": {},
          "document_table_count": 0, "elapsed_seconds": 0.001},
        "insights": ["Top label: Dog (99.2%)"]
      }],
      "batch": {"report_count": 4, "feature_coverage": {"classification": 1, "detection": 1},
        "top_labels": {"Dog": 1}, "object_counts": {"Dog": 5}, "total_faces": 1,
        "total_ocr_lines": 2, "total_document_fields": 2, "reports": []},
      "comparisons": [{"slug": "dog-vs-sign", "title": "Animal vs sign", "summary": {}}],
      "workflows": {
        "receipt": {"field_count": 2, "fields": {"Invoice Number": "INV-1001"}, "table_count": 1, "page_count": 1},
        "shelf": {"object_count": 11, "objects": {"Dog": 5}},
        "inspection": {"classification": ["Dog"], "detection": {"Dog": 5}, "text": ""},
        "archive_search": {"query": "INV-1001", "match_count": 1,
          "matches": [{"image": "invoice_demo.png", "page_count": 1, "field_count": 2}]}
      },
      "commands": {"showcase": "oci-vision showcase --demo"},
      "headlines": ["4 curated demo assets cover 5 vision feature(s)."]
    }`

	showcase, err := Decode[Showcase]([]byte(showcaseJSON))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	if showcase.AssetCount != 4 || showcase.WorkflowCount != 4 || showcase.ComparisonCount != 2 {
		t.Errorf("counts = %d/%d/%d", showcase.AssetCount, showcase.WorkflowCount, showcase.ComparisonCount)
	}
	if len(showcase.Gallery) != 1 || showcase.Gallery[0].Summary.TopLabel != "Dog" {
		t.Errorf("gallery = %+v", showcase.Gallery)
	}
	if showcase.Batch.ReportCount != 4 || showcase.Batch.TotalOCRLines != 2 {
		t.Errorf("batch = %+v", showcase.Batch)
	}
	if len(showcase.Headlines) != 1 {
		t.Errorf("headlines = %v", showcase.Headlines)
	}
	// Each workflow has its own shape and must land in its own field.
	if showcase.Workflows.Receipt.Fields["Invoice Number"] != "INV-1001" {
		t.Errorf("receipt = %+v", showcase.Workflows.Receipt)
	}
	if showcase.Workflows.Shelf.Objects["Dog"] != 5 {
		t.Errorf("shelf = %+v", showcase.Workflows.Shelf)
	}
	if len(showcase.Workflows.ArchiveSearch.Matches) != 1 {
		t.Errorf("archive search = %+v", showcase.Workflows.ArchiveSearch)
	}
}

func TestDecodeWorkflowShapes(t *testing.T) {
	receipt, err := Decode[ReceiptWorkflow]([]byte(
		`{"field_count":2,"fields":{"Invoice Number":"INV-1001"},"table_count":1,"page_count":1}`))
	if err != nil {
		t.Fatalf("receipt: %v", err)
	}
	if receipt.Fields["Invoice Number"] != "INV-1001" {
		t.Errorf("receipt fields = %+v", receipt.Fields)
	}

	archive, err := Decode[ArchiveSearchWorkflow]([]byte(
		`{"query":"INV-1001","match_count":1,"matches":[{"image":"invoice_demo.png","page_count":1,"field_count":2}]}`))
	if err != nil {
		t.Fatalf("archive-search: %v", err)
	}
	if archive.MatchCount != 1 || archive.Matches[0].Image != "invoice_demo.png" {
		t.Errorf("archive = %+v", archive)
	}
}

// TestDecodeReportsTheOffendingValue keeps a schema drift visible instead of
// returning a zero value the UI would render as blank.
func TestDecodeReportsTheOffendingValue(t *testing.T) {
	_, err := Decode[Analysis]([]byte(`{"image_path": 42}`))
	if err == nil {
		t.Fatal("a wrong-typed field must be reported")
	}
}
