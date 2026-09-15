package tui

import (
	"strconv"
	"strings"

	"charm.land/lipgloss/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/huhstyle"
	"github.com/jasperan/oci-vision-ai/gotui/internal/report"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// minPaneWidth is the narrowest a panel's CONTENT area is allowed to render at.
//
// A terminal narrower than this is common in a split pane, and rendering below it
// produced borders narrower than their own title. Clamping is what keeps a narrow
// window from panicking on a negative repeat count.
const minPaneWidth = 20

// paneChrome is the columns a pane spends on its own frame: a 2-column border plus
// 2 columns of padding on each side.
//
// It exists because lipgloss Width(w) sets the block's TOTAL width, frame included,
// so its content area is only w - paneChrome. Measured, not assumed:
// lipgloss.NewStyle().Border(RoundedBorder()).Padding(1, 2).Width(w) renders exactly
// w columns, with w - 6 available for text.
//
// Getting this wrong is not cosmetic: the report is 6 columns narrower or wider
// than the terminal, and every box or bar row wraps at exactly the moment the user
// is trying to read it.
const paneChrome = 6

// minPaneTotal is the narrowest a pane's TOTAL width may be, so its content area
// never drops below minPaneWidth.
const minPaneTotal = minPaneWidth + paneChrome

// innerWidth converts the total columns a pane occupies into the content width
// available inside its frame.
func innerWidth(total int) int {
	inner := total - paneChrome
	if inner < minPaneWidth {
		inner = minPaneWidth
	}
	return inner
}

// palette derives every colour from the theme, never declaring a literal here.
//
// Reading the compiled styles back out of internal/huhstyle keeps one definition
// of each token: a colour written in this file would instantly diverge from the
// forms the user is looking at.
func palette() (primary, text, subtext, muted, danger, success lipgloss.Style) {
	styles := huhstyle.Styles()
	return lipgloss.NewStyle().Foreground(styles.Focused.Title.GetForeground()),
		lipgloss.NewStyle().Foreground(styles.Focused.Option.GetForeground()),
		lipgloss.NewStyle().Foreground(styles.Focused.Description.GetForeground()),
		lipgloss.NewStyle().Foreground(styles.Focused.TextInput.Placeholder.GetForeground()),
		lipgloss.NewStyle().Foreground(styles.Focused.ErrorMessage.GetForeground()),
		lipgloss.NewStyle().Foreground(styles.Focused.SelectedOption.GetForeground())
}

// Pane renders a titled panel: rounded border, generous padding, primary title.
//
// width is the TOTAL number of columns the pane occupies, frame included, which is
// exactly what lipgloss Width expects.
func Pane(title, body string, width int) string {
	primary, text, _, _, _, _ := palette()

	if width < minPaneTotal {
		width = minPaneTotal
	}

	heading := ""
	if title != "" {
		heading = primary.Bold(true).Render(title) + "\n"
	}
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		Padding(1, 2).
		Width(width).
		Render(heading + text.Render(body))
}

// PaneError renders an error panel.
//
// A failed analysis is a normal state for this front-end, not a crash: the user
// gets the CLI's own message and a way onward.
func PaneError(title string, err error, width int) string {
	_, _, _, _, danger, _ := palette()
	message := "unknown error"
	if err != nil {
		message = err.Error()
	}
	return Pane(title, danger.Render(message), width)
}

// Heading renders a bold identity line, for content that already carries its own
// framing.
//
// It exists so a report is not wrapped in an outer pane: the report is already a
// stack of panes, and boxing that again made the inner frames wider than their
// container and wrap.
func Heading(text string, width int) string {
	primary, _, _, _, _, _ := palette()
	if lipgloss.Width(text) > width {
		text = Truncate(text, width)
	}
	return primary.Bold(true).Render(text)
}

// Fog renders low-emphasis body text.
func Fog(body string) string {
	_, _, subtext, _, _, _ := palette()
	return subtext.Render(body)
}

// Stat renders one "label: value" readout line.
func Stat(label, value string) string {
	_, text, subtext, _, _, _ := palette()
	return subtext.Render(label+": ") + text.Render(value)
}

// Header is the persistent identity bar.
func Header(demo bool, width int) string {
	primary, _, subtext, _, _, _ := palette()
	mode := "live"
	if demo {
		mode = "demo"
	}
	title := primary.Bold(true).Render("oci-vision") + " " + subtext.Render("Go front-end")
	right := subtext.Render(mode + " mode")
	gap := width - lipgloss.Width(title) - lipgloss.Width(right) - 4
	if gap < 1 {
		gap = 1
	}
	return title + strings.Repeat(" ", gap) + right
}

// Footer is the key-hint bar.
func Footer(hint string, width int) string {
	_, _, subtext, _, _, _ := palette()
	if lipgloss.Width(hint) > width-2 {
		hint = Truncate(hint, width-2)
	}
	return subtext.Render(hint)
}

// ConfidenceBar renders a fixed-width bar for a 0..1 confidence.
//
// The bar is the point of this front-end: a column of percentages is unreadable
// at a glance, and the ranking is the actual finding.
func ConfidenceBar(value float64, cells int) string {
	if cells < 4 {
		cells = 4
	}
	if value < 0 {
		value = 0
	}
	if value > 1 {
		value = 1
	}
	filled := int(value*float64(cells) + 0.5)
	if filled > cells {
		filled = cells
	}
	_, _, _, muted, _, success := palette()
	return success.Render(strings.Repeat("█", filled)) +
		muted.Render(strings.Repeat("░", cells-filled))
}

// ClassificationRows renders labels as ranked bars.
func ClassificationRows(result *report.ClassificationResult, width int) string {
	if result == nil || len(result.Labels) == 0 {
		return "No labels were returned."
	}
	_, text, subtext, _, _, _ := palette()

	// A row is: label(pad labelWidth) + 2 + bar(12) + 2 + score(~6).
	labelWidth := width - 24
	if labelWidth < 10 {
		labelWidth = 10
	}

	var out strings.Builder
	for _, label := range result.Labels {
		out.WriteString(text.Render(Pad(Truncate(label.Name, labelWidth), labelWidth)) + "  ")
		out.WriteString(ConfidenceBar(label.Confidence, 12) + "  ")
		out.WriteString(subtext.Render(FormatPct(label.ConfidencePct)) + "\n")
	}
	if result.ModelVersion != "" {
		out.WriteString("\n" + subtext.Render("model "+result.ModelVersion))
	}
	return strings.TrimRight(out.String(), "\n")
}

// DetectionRows renders detected objects as an aligned table.
func DetectionRows(result *report.DetectionResult, width int) string {
	if result == nil || len(result.Objects) == 0 {
		return "No objects were detected."
	}
	_, text, _, muted, _, _ := palette()

	// A row is: name(pad nameWidth) + 2 + confidence(12) + 2 + position(~14).
	nameWidth := width - 32
	if nameWidth < 10 {
		nameWidth = 10
	}

	var out strings.Builder
	out.WriteString(muted.Render(Pad("object", nameWidth)+"  "+Pad("confidence", 12)+"  position") + "\n")
	for _, object := range result.Objects {
		out.WriteString(text.Render(Pad(Truncate(object.Name, nameWidth), nameWidth)) + "  ")
		out.WriteString(text.Render(Pad(FormatPct(object.ConfidencePct), 12)) + "  ")
		out.WriteString(text.Render(CenterLabel(object.BoundingPolygon)) + "\n")
	}
	out.WriteString("\n" + muted.Render(strconv.Itoa(len(result.Objects))+" object(s)"))
	if result.ModelVersion != "" {
		out.WriteString(muted.Render(" - model " + result.ModelVersion))
	}
	return out.String()
}

// CenterLabel renders a detection's normalized center as a percentage pair.
func CenterLabel(poly report.BoundingPolygon) string {
	if len(poly.Center) < 2 {
		return "-"
	}
	return FormatPct(poly.Center[0]*100) + ", " + FormatPct(poly.Center[1]*100)
}

// TextRows renders OCR lines with their confidence.
func TextRows(result *report.TextResult, width int) string {
	if result == nil || len(result.Lines) == 0 {
		return "No text was found."
	}
	_, text, subtext, _, _, _ := palette()

	var out strings.Builder
	for _, line := range result.Lines {
		out.WriteString(text.Render(Truncate(line.Text, width-20)) + "  ")
		out.WriteString(subtext.Render(FormatPct(line.Confidence*100)) + "\n")
	}
	if result.FullText != "" {
		out.WriteString("\n" + subtext.Render("full text: "+strings.ReplaceAll(result.FullText, "\n", " / ")))
	}
	return out.String()
}

// FaceRows renders detected faces and their landmark counts.
func FaceRows(result *report.FaceResult, width int) string {
	if result == nil || len(result.Faces) == 0 {
		return "No faces were detected."
	}
	_, text, subtext, _, _, _ := palette()

	var out strings.Builder
	for i, face := range result.Faces {
		out.WriteString(text.Render("face "+strconv.Itoa(i+1)) + "  ")
		out.WriteString(ConfidenceBar(face.Confidence, 12) + "  ")
		out.WriteString(subtext.Render(FormatPct(face.Confidence*100)) + "\n")
		out.WriteString(subtext.Render("  center "+CenterLabel(face.BoundingPolygon)+
			"  landmarks "+strconv.Itoa(len(face.Landmarks))) + "\n")
	}
	return strings.TrimRight(out.String(), "\n")
}

// DocumentRows renders extracted fields and tables.
func DocumentRows(result *report.DocumentResult, width int) string {
	if result == nil {
		return "No document result was returned."
	}
	_, text, subtext, muted, _, _ := palette()

	labelWidth := width - 24
	if labelWidth < 10 {
		labelWidth = 10
	}

	var out strings.Builder
	out.WriteString(subtext.Render(strconv.Itoa(result.PageCount)+" page(s), "+
		strconv.Itoa(len(result.Fields))+" field(s), "+
		strconv.Itoa(len(result.Tables))+" table(s)") + "\n")

	for _, field := range result.Fields {
		out.WriteString("\n" + text.Render(Pad(Truncate(field.Label, labelWidth), labelWidth)) + "  ")
		out.WriteString(text.Render(field.Value) + "  ")
		out.WriteString(muted.Render(FormatPct(field.Confidence * 100)))
	}

	for i, table := range result.Tables {
		out.WriteString("\n\n" + subtext.Render("table "+strconv.Itoa(i+1)) + "\n")
		if len(table.HeaderRows) > 0 {
			out.WriteString(muted.Render(strings.Join(table.HeaderRows, "  |  ")) + "\n")
		}
		for _, row := range table.BodyRows {
			out.WriteString(text.Render(strings.Join(row, "  |  ")) + "\n")
		}
	}
	return strings.TrimRight(out.String(), "\n")
}

// InsightRows renders the CLI's own insight lines.
func InsightRows(insights []string) string {
	if len(insights) == 0 {
		return ""
	}
	_, text, _, _, _, _ := palette()
	lines := make([]string, 0, len(insights))
	for _, insight := range insights {
		lines = append(lines, text.Render("- "+insight))
	}
	return strings.Join(lines, "\n")
}

// AnalysisReport renders a complete analysis: one pane per feature present.
//
// width is the total columns available; each pane draws its frame inside that, and
// the row renderers are given the content width so their columns line up.
//
// Only the features the CLI actually returned are drawn, so a fixture that only
// backs classification is not presented with three empty sections.
func AnalysisReport(analysis report.Analysis, width int) string {
	inner := innerWidth(width)
	var out strings.Builder

	if len(analysis.Insights) > 0 {
		out.WriteString(Pane("Insights", InsightRows(analysis.Insights), width) + "\n\n")
	}
	if analysis.Classification != nil {
		out.WriteString(Pane("Classification", ClassificationRows(analysis.Classification, inner), width) + "\n\n")
	}
	if analysis.Detection != nil {
		out.WriteString(Pane("Object detection", DetectionRows(analysis.Detection, inner), width) + "\n\n")
	}
	if analysis.Text != nil {
		out.WriteString(Pane("Text / OCR", TextRows(analysis.Text, inner), width) + "\n\n")
	}
	if analysis.Faces != nil {
		out.WriteString(Pane("Face detection", FaceRows(analysis.Faces, inner), width) + "\n\n")
	}
	if analysis.Document != nil {
		out.WriteString(Pane("Document AI", DocumentRows(analysis.Document, inner), width) + "\n\n")
	}
	if len(analysis.AvailableFeatures) == 0 {
		out.WriteString(Pane("Result", "The CLI returned no feature results for this image.", width) + "\n\n")
	}
	return out.String()
}

// ComparisonReport renders the output of `oci-vision compare`.
func ComparisonReport(comparison report.Comparison, width int) string {
	inner := innerWidth(width)
	var out strings.Builder

	out.WriteString(Pane("Summary",
		Stat("left", comparison.LeftImage)+"\n"+
			Stat("right", comparison.RightImage)+"\n"+
			Stat("shared features", JoinOrDash(comparison.SharedFeatures))+"\n"+
			Stat("left only", JoinOrDash(comparison.LeftOnlyFeatures))+"\n"+
			Stat("right only", JoinOrDash(comparison.RightOnlyFeatures)), width) + "\n\n")

	out.WriteString(Pane("Top label",
		Stat("left", comparison.TopLabelChange.Left)+"\n"+
			Stat("right", comparison.TopLabelChange.Right)+"\n"+
			Stat("changed", strconv.FormatBool(comparison.TopLabelChange.Changed)), width) + "\n\n")

	var deltas strings.Builder
	deltas.WriteString(Stat("object count change", FormatDelta(comparison.ObjectCountDelta)) + "\n")
	deltas.WriteString(Stat("ocr line change", FormatDelta(comparison.OCRLineDelta)) + "\n")
	deltas.WriteString(Stat("face count change", FormatDelta(comparison.FaceCountDelta)) + "\n")
	deltas.WriteString(Stat("document field change", FormatDelta(comparison.DocumentFieldDelta)) + "\n")
	if comparison.OCRSimilarity != nil {
		deltas.WriteString(Stat("ocr similarity", FormatPct(*comparison.OCRSimilarity*100)) + "\n")
	}
	out.WriteString(Pane("Deltas", strings.TrimRight(deltas.String(), "\n"), width) + "\n\n")

	if len(comparison.ObjectDeltas) > 0 {
		_, text, _, muted, _, _ := palette()
		nameWidth := inner - 24
		if nameWidth < 10 {
			nameWidth = 10
		}
		var rows strings.Builder
		rows.WriteString(muted.Render(Pad("object", nameWidth)+"  "+Pad("left", 6)+"  "+Pad("right", 6)+"  change") + "\n")
		for _, delta := range comparison.ObjectDeltas {
			rows.WriteString(text.Render(Pad(Truncate(delta.Name, nameWidth), nameWidth)) + "  ")
			rows.WriteString(text.Render(Pad(strconv.Itoa(delta.Left), 6)) + "  ")
			rows.WriteString(text.Render(Pad(strconv.Itoa(delta.Right), 6)) + "  ")
			rows.WriteString(text.Render(FormatDelta(delta.Delta)) + "\n")
		}
		out.WriteString(Pane("Object changes", strings.TrimRight(rows.String(), "\n"), width) + "\n\n")
	}

	if len(comparison.DocumentFieldChanges) > 0 {
		_, text, _, _, _, _ := palette()
		var rows strings.Builder
		for _, change := range comparison.DocumentFieldChanges {
			rows.WriteString(text.Render(change.Label) + "  ")
			rows.WriteString(text.Render(DerefOrDash(change.Left)) + " -> ")
			rows.WriteString(text.Render(DerefOrDash(change.Right)) + "\n")
		}
		out.WriteString(Pane("Document field changes", strings.TrimRight(rows.String(), "\n"), width) + "\n\n")
	}

	return out.String()
}

// ShowcaseReport renders the output of `oci-vision showcase`.
func ShowcaseReport(showcase report.Showcase, width int) string {
	var out strings.Builder

	if len(showcase.Headlines) > 0 {
		_, text, _, _, _, _ := palette()
		lines := make([]string, 0, len(showcase.Headlines))
		for _, headline := range showcase.Headlines {
			lines = append(lines, text.Render("- "+headline))
		}
		out.WriteString(Pane("Headlines", strings.Join(lines, "\n"), width) + "\n\n")
	}

	out.WriteString(Pane("Snapshot",
		Stat("assets", strconv.Itoa(showcase.AssetCount))+"\n"+
			Stat("workflows", strconv.Itoa(showcase.WorkflowCount))+"\n"+
			Stat("comparisons", strconv.Itoa(showcase.ComparisonCount))+"\n"+
			Stat("generated", showcase.GeneratedAt), width) + "\n\n")

	if len(showcase.Gallery) > 0 {
		_, text, _, muted, _, _ := palette()
		var rows strings.Builder
		for _, asset := range showcase.Gallery {
			rows.WriteString(text.Render(asset.Filename) + "\n")
			rows.WriteString(muted.Render("  "+asset.Summary.TopLabel+" - "+
				strconv.Itoa(asset.Summary.ObjectCount)+" object(s), "+
				strconv.Itoa(asset.Summary.OCRLineCount)+" OCR line(s)") + "\n")
		}
		out.WriteString(Pane("Gallery", strings.TrimRight(rows.String(), "\n"), width) + "\n\n")
	}

	if showcase.Batch.ReportCount > 0 {
		batch := showcase.Batch
		var rows strings.Builder
		rows.WriteString(Stat("reports", strconv.Itoa(batch.ReportCount)) + "\n")
		rows.WriteString(Stat("faces", strconv.Itoa(batch.TotalFaces)) + "\n")
		rows.WriteString(Stat("ocr lines", strconv.Itoa(batch.TotalOCRLines)) + "\n")
		rows.WriteString(Stat("document fields", strconv.Itoa(batch.TotalDocumentFields)) + "\n")
		rows.WriteString(Stat("features covered", JoinOrDash(run.SortedKeys(batch.FeatureCoverage))))
		out.WriteString(Pane("Batch", rows.String(), width) + "\n\n")
	}

	return out.String()
}

// WorkflowReport renders one workflow result.
//
// The JSON is decoded into the workflow's own types, but unknown shapes (a
// workflow added by a future release) still render, because the raw JSON is
// shown as a fallback rather than dropped.
func WorkflowReport(kind string, raw []byte, width int) string {
	switch kind {
	case "receipt":
		value, err := report.Decode[report.ReceiptWorkflow](raw)
		if err != nil {
			return Pane("Receipt", rawFallback(raw, err), width)
		}
		_, text, _, _, _, _ := palette()
		var rows strings.Builder
		rows.WriteString(Stat("fields", strconv.Itoa(value.FieldCount)) + "\n")
		rows.WriteString(Stat("tables", strconv.Itoa(value.TableCount)) + "\n")
		rows.WriteString(Stat("pages", strconv.Itoa(value.PageCount)) + "\n")
		for _, label := range run.SortedKeys(value.Fields) {
			rows.WriteString("\n" + text.Render(label+": ") + text.Render(value.Fields[label]))
		}
		return Pane("Receipt", rows.String(), width)

	case "shelf":
		value, err := report.Decode[report.ShelfWorkflow](raw)
		if err != nil {
			return Pane("Shelf audit", rawFallback(raw, err), width)
		}
		_, text, _, _, _, _ := palette()
		var rows strings.Builder
		rows.WriteString(Stat("objects", strconv.Itoa(value.ObjectCount)) + "\n")
		for _, name := range run.SortedKeys(value.Objects) {
			rows.WriteString("\n" + text.Render(name+": ") + text.Render(strconv.Itoa(value.Objects[name])))
		}
		return Pane("Shelf audit", rows.String(), width)

	case "inspection":
		value, err := report.Decode[report.InspectionWorkflow](raw)
		if err != nil {
			return Pane("Inspection", rawFallback(raw, err), width)
		}
		_, text, _, _, _, _ := palette()
		var rows strings.Builder
		rows.WriteString(Stat("classification", JoinOrDash(value.Classification)) + "\n")
		for _, name := range run.SortedKeys(value.Detection) {
			rows.WriteString("\n" + text.Render(name+": ") + text.Render(strconv.Itoa(value.Detection[name])))
		}
		if value.Text != "" {
			rows.WriteString("\n" + Stat("text", value.Text))
		}
		return Pane("Inspection", rows.String(), width)

	case "archive-search":
		value, err := report.Decode[report.ArchiveSearchWorkflow](raw)
		if err != nil {
			return Pane("Archive search", rawFallback(raw, err), width)
		}
		_, text, _, _, _, _ := palette()
		var rows strings.Builder
		rows.WriteString(Stat("query", value.Query) + "\n")
		rows.WriteString(Stat("matches", strconv.Itoa(value.MatchCount)))
		for _, match := range value.Matches {
			rows.WriteString("\n" + text.Render(match.Image+"  "+
				strconv.Itoa(match.PageCount)+" page(s), "+
				strconv.Itoa(match.FieldCount)+" field(s)"))
		}
		return Pane("Archive search", rows.String(), width)

	default:
		return Pane("Workflow", string(raw), width)
	}
}

// rawFallback keeps an undecodable payload visible instead of hiding it.
func rawFallback(raw []byte, err error) string {
	return err.Error() + "\n\n" + string(raw)
}

// Pad right-pads to n columns.
func Pad(s string, n int) string {
	width := lipgloss.Width(s)
	if width >= n {
		return s
	}
	return s + strings.Repeat(" ", n-width)
}

// Truncate shortens s to n columns, adding an ellipsis when it cuts.
//
// It is display-width aware, not rune-count aware: a CJK label in an OCR result
// is two columns per rune, and a rune-count truncation would overflow the pane.
func Truncate(s string, n int) string {
	if n <= 1 {
		return s
	}
	if lipgloss.Width(s) <= n {
		return s
	}
	runes := []rune(s)
	for len(runes) > 0 && lipgloss.Width(string(runes))+1 > n {
		runes = runes[:len(runes)-1]
	}
	return string(runes) + "~"
}

// FormatPct renders a percentage with one decimal place.
func FormatPct(value float64) string {
	return strconv.FormatFloat(value, 'f', 1, 64) + "%"
}

// FormatDelta renders a signed change, so a decrease is never read as an increase.
func FormatDelta(value int) string {
	if value > 0 {
		return "+" + strconv.Itoa(value)
	}
	return strconv.Itoa(value)
}

// JoinOrDash renders a string slice, or a dash when it is empty.
func JoinOrDash(values []string) string {
	if len(values) == 0 {
		return "-"
	}
	return strings.Join(values, ", ")
}

// DerefOrDash renders an optional string, or a dash when it is absent.
func DerefOrDash(value *string) string {
	if value == nil {
		return "-"
	}
	return *value
}
