// Package report holds the JSON shapes this front-end reads back from the
// oci-vision CLI.
//
// Every struct here mirrors a Pydantic model in src/oci_vision/core/models.py
// and src/oci_vision/core/insights.py, and the field names were taken from
// `oci-vision ... --output-format json` output, not guessed. Nothing in this
// package analyses an image: it only decodes what the Python CLI already
// decided, so a Go user and a Python user see the same numbers.
package report

import (
	"encoding/json"
	"fmt"
)

// Vertex is a normalized image coordinate.
type Vertex struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// BoundingPolygon is the normalized quadrilateral around a detection.
type BoundingPolygon struct {
	NormalizedVertices []Vertex  `json:"normalized_vertices"`
	Center             []float64 `json:"center"`
}

// ClassificationLabel is one image label.
type ClassificationLabel struct {
	Name          string  `json:"name"`
	Confidence    float64 `json:"confidence"`
	ConfidencePct float64 `json:"confidence_pct"`
}

// ClassificationResult mirrors models.py:ClassificationResult.
type ClassificationResult struct {
	ModelVersion string                `json:"model_version"`
	Labels       []ClassificationLabel `json:"labels"`
}

// DetectedObject is one detected object.
type DetectedObject struct {
	Name            string          `json:"name"`
	Confidence      float64         `json:"confidence"`
	BoundingPolygon BoundingPolygon `json:"bounding_polygon"`
	ConfidencePct   float64         `json:"confidence_pct"`
}

// DetectionResult mirrors models.py:DetectionResult.
type DetectionResult struct {
	ModelVersion string           `json:"model_version"`
	Objects      []DetectedObject `json:"objects"`
}

// TextWord is one recognized word.
type TextWord struct {
	Text            string          `json:"text"`
	Confidence      float64         `json:"confidence"`
	BoundingPolygon BoundingPolygon `json:"bounding_polygon"`
}

// TextLine is one recognized line of text.
type TextLine struct {
	Text            string          `json:"text"`
	Confidence      float64         `json:"confidence"`
	BoundingPolygon BoundingPolygon `json:"bounding_polygon"`
	Words           []TextWord      `json:"words"`
}

// TextResult mirrors models.py:TextDetectionResult.
type TextResult struct {
	ModelVersion string     `json:"model_version"`
	Lines        []TextLine `json:"lines"`
	FullText     string     `json:"full_text"`
}

// FaceLandmark is one facial landmark.
type FaceLandmark struct {
	Type string  `json:"type"`
	X    float64 `json:"x"`
	Y    float64 `json:"y"`
}

// DetectedFace is one detected face.
type DetectedFace struct {
	Confidence      float64         `json:"confidence"`
	BoundingPolygon BoundingPolygon `json:"bounding_polygon"`
	Landmarks       []FaceLandmark  `json:"landmarks"`
}

// FaceResult mirrors models.py:FaceDetectionResult.
type FaceResult struct {
	ModelVersion string         `json:"model_version"`
	Faces        []DetectedFace `json:"faces"`
}

// DocumentField is one extracted key/value pair.
type DocumentField struct {
	FieldType  string  `json:"field_type"`
	Label      string  `json:"label"`
	Value      string  `json:"value"`
	Confidence float64 `json:"confidence"`
}

// DocumentTable is one extracted table.
type DocumentTable struct {
	RowCount    int        `json:"row_count"`
	ColumnCount int        `json:"column_count"`
	HeaderRows  []string   `json:"header_rows"`
	BodyRows    [][]string `json:"body_rows"`
	Confidence  float64    `json:"confidence"`
}

// DocumentResult mirrors models.py:DocumentResult.
type DocumentResult struct {
	ModelVersion string          `json:"model_version"`
	Fields       []DocumentField `json:"fields"`
	Tables       []DocumentTable `json:"tables"`
	FullText     string          `json:"full_text"`
	PageCount    int             `json:"page_count"`
}

// Analysis mirrors models.py:AnalysisReport, including the two fields the CLI
// adds when it serializes a report: available_features (a computed field) and
// insights (from core/insights.py:report_insights).
type Analysis struct {
	ImagePath         string                `json:"image_path"`
	Classification    *ClassificationResult `json:"classification"`
	Detection         *DetectionResult      `json:"detection"`
	Text              *TextResult           `json:"text"`
	Faces             *FaceResult           `json:"faces"`
	Document          *DocumentResult       `json:"document"`
	ElapsedSeconds    float64               `json:"elapsed_seconds"`
	AvailableFeatures []string              `json:"available_features"`
	Insights          []string              `json:"insights"`
}

// Summary is the per-report roll-up produced by insights.py:summarize_report.
type Summary struct {
	Image              string            `json:"image"`
	Features           []string          `json:"features"`
	FeatureCount       int               `json:"feature_count"`
	TopLabel           string            `json:"top_label"`
	TopConfidencePct   *float64          `json:"top_confidence_pct"`
	ObjectCount        int               `json:"object_count"`
	ObjectCounts       map[string]int    `json:"object_counts"`
	OCRLineCount       int               `json:"ocr_line_count"`
	OCRPreview         string            `json:"ocr_preview"`
	FaceCount          int               `json:"face_count"`
	DocumentFieldCount int               `json:"document_field_count"`
	DocumentFields     map[string]string `json:"document_fields"`
	DocumentTableCount int               `json:"document_table_count"`
	ElapsedSeconds     float64           `json:"elapsed_seconds"`
}

// LabelChange is the top-label transition between two reports.
type LabelChange struct {
	Left    string `json:"left"`
	Right   string `json:"right"`
	Changed bool   `json:"changed"`
}

// ObjectDelta is the per-object count change between two reports.
type ObjectDelta struct {
	Name  string `json:"name"`
	Left  int    `json:"left"`
	Right int    `json:"right"`
	Delta int    `json:"delta"`
}

// FieldChange is one changed document field between two reports.
type FieldChange struct {
	Label   string  `json:"label"`
	Left    *string `json:"left"`
	Right   *string `json:"right"`
	Changed bool    `json:"changed"`
}

// Comparison mirrors insights.py:compare_reports.
type Comparison struct {
	LeftImage            string        `json:"left_image"`
	RightImage           string        `json:"right_image"`
	SharedFeatures       []string      `json:"shared_features"`
	LeftOnlyFeatures     []string      `json:"left_only_features"`
	RightOnlyFeatures    []string      `json:"right_only_features"`
	TopLabelChange       LabelChange   `json:"top_label_change"`
	ObjectCountDelta     int           `json:"object_count_delta"`
	ObjectDeltas         []ObjectDelta `json:"object_deltas"`
	OCRSimilarity        *float64      `json:"ocr_similarity"`
	OCRLineDelta         int           `json:"ocr_line_delta"`
	FaceCountDelta       int           `json:"face_count_delta"`
	DocumentFieldDelta   int           `json:"document_field_delta"`
	DocumentFieldChanges []FieldChange `json:"document_field_changes"`
	LeftSummary          Summary       `json:"left_summary"`
	RightSummary         Summary       `json:"right_summary"`
}

// Batch mirrors insights.py:summarize_batch.
type Batch struct {
	ReportCount         int            `json:"report_count"`
	FeatureCoverage     map[string]int `json:"feature_coverage"`
	TopLabels           map[string]int `json:"top_labels"`
	ObjectCounts        map[string]int `json:"object_counts"`
	TotalFaces          int            `json:"total_faces"`
	TotalOCRLines       int            `json:"total_ocr_lines"`
	TotalDocumentFields int            `json:"total_document_fields"`
	Reports             []Summary      `json:"reports"`
}

// ShowcaseAsset is one gallery entry inside the showcase snapshot.
type ShowcaseAsset struct {
	ID                  string   `json:"id"`
	Filename            string   `json:"filename"`
	Description         string   `json:"description"`
	RecommendedFeatures []string `json:"recommended_features"`
	Command             string   `json:"command"`
	Summary             Summary  `json:"summary"`
	Insights            []string `json:"insights"`
}

// ShowcaseComparison is one preset comparison inside the showcase snapshot.
type ShowcaseComparison struct {
	Slug    string     `json:"slug"`
	Title   string     `json:"title"`
	Summary Comparison `json:"summary"`
}

// ReceiptWorkflow mirrors workflows/receipts.py's return value.
type ReceiptWorkflow struct {
	FieldCount int               `json:"field_count"`
	Fields     map[string]string `json:"fields"`
	TableCount int               `json:"table_count"`
	PageCount  int               `json:"page_count"`
}

// ShelfWorkflow mirrors workflows/shelf_audit.py's return value.
type ShelfWorkflow struct {
	ObjectCount int            `json:"object_count"`
	Objects     map[string]int `json:"objects"`
}

// InspectionWorkflow mirrors workflows/inspection.py's return value.
type InspectionWorkflow struct {
	Classification []string       `json:"classification"`
	Detection      map[string]int `json:"detection"`
	Text           string         `json:"text"`
}

// ArchiveMatch is one archive-search hit.
type ArchiveMatch struct {
	Image      string `json:"image"`
	PageCount  int    `json:"page_count"`
	FieldCount int    `json:"field_count"`
}

// ArchiveSearchWorkflow mirrors workflows/archive_search.py's return value.
type ArchiveSearchWorkflow struct {
	Query      string         `json:"query"`
	MatchCount int            `json:"match_count"`
	Matches    []ArchiveMatch `json:"matches"`
}

// Workflows is the showcase's per-workflow roll-up. Each workflow returns its own
// shape, so each gets its own field rather than a generic map.
type Workflows struct {
	Receipt       ReceiptWorkflow       `json:"receipt"`
	Shelf         ShelfWorkflow         `json:"shelf"`
	Inspection    InspectionWorkflow    `json:"inspection"`
	ArchiveSearch ArchiveSearchWorkflow `json:"archive_search"`
}

// Showcase mirrors core/showcase.py:build_showcase_snapshot.
type Showcase struct {
	GeneratedAt     string               `json:"generated_at"`
	Demo            bool                 `json:"demo"`
	AssetCount      int                  `json:"asset_count"`
	WorkflowCount   int                  `json:"workflow_count"`
	ComparisonCount int                  `json:"comparison_count"`
	Gallery         []ShowcaseAsset      `json:"gallery"`
	Batch           Batch                `json:"batch"`
	Comparisons     []ShowcaseComparison `json:"comparisons"`
	Workflows       Workflows            `json:"workflows"`
	Commands        map[string]string    `json:"commands"`
	Headlines       []string             `json:"headlines"`
}

// Decode parses one of the CLI's JSON documents.
//
// Callers pass the value they expect, so an unexpected payload fails with the
// decoder's own message rather than silently decoding into an empty struct.
func Decode[T any](data []byte) (T, error) {
	var value T
	if err := json.Unmarshal(data, &value); err != nil {
		return value, fmt.Errorf("decode %T: %w", value, err)
	}
	return value, nil
}
