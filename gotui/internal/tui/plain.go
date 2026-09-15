package tui

import (
	"fmt"
	"io"
	"strconv"
	"strings"
	"time"

	"github.com/jasperan/oci-vision-ai/gotui/internal/cli"
	"github.com/jasperan/oci-vision-ai/gotui/internal/report"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// PlainOptions drive the non-interactive path.
//
// This path is used when stdin is not a terminal, when ACCESSIBLE is set, and
// whenever an action flag is passed. It renders the SAME decoded payloads as the
// TUI but without styling, so a pipe gets text and a terminal gets colour from
// the same code.
type PlainOptions struct {
	Exec    Executor
	Binary  string
	Timeout time.Duration
	Out     io.Writer
	// JSON prints the CLI's own JSON document untouched, for scripts.
	JSON bool
}

// RunPlan executes a resolved plan and writes its result.
func RunPlan(plan cli.Plan, opts PlainOptions) error {
	if opts.Out == nil {
		opts.Out = io.Discard
	}
	if opts.Timeout <= 0 {
		opts.Timeout = DefaultTimeout
	}

	inv, kind, passthrough, err := invocationFor(plan, opts.Binary)
	if err != nil {
		return err
	}

	raw, runErr := opts.Exec.Run(inv, opts.Timeout)
	if runErr != nil {
		// The CLI's own message is the report; the command line makes it
		// reproducible.
		fmt.Fprintf(opts.Out, "error: %s\n", runErr.Error())
		fmt.Fprintf(opts.Out, "$ %s\n", inv.CommandLine())
		if len(raw) > 0 {
			fmt.Fprintln(opts.Out, strings.TrimRight(stripANSI(string(raw)), "\n"))
		}
		return runErr
	}

	if opts.JSON || passthrough {
		fmt.Fprintln(opts.Out, strings.TrimRight(stripANSI(string(raw)), "\n"))
		return nil
	}

	body, err := plainBody(kind, raw)
	if err != nil {
		return err
	}
	fmt.Fprintln(opts.Out, body)
	return nil
}

// invocationFor maps a plan to the invocation that performs it.
func invocationFor(plan cli.Plan, binary string) (inv run.Invocation, kind string, passthrough bool, err error) {
	switch plan.Action {
	case cli.ActionAnalyze:
		if err := run.ValidateFeatureNames(plan.Features); err != nil {
			return run.Invocation{}, "", false, err
		}
		return run.Analyze(binary, plan.Image, plan.Features, plan.ModelID, plan.Demo), "analysis", false, nil

	case cli.ActionCompare:
		if err := run.ValidateFeatureNames(plan.Features); err != nil {
			return run.Invocation{}, "", false, err
		}
		return run.Compare(binary, plan.Left, plan.Right, plan.Features, plan.Demo), "comparison", false, nil

	case cli.ActionFeature:
		inv, err := run.Feature(binary, plan.Feature, plan.Image, plan.ModelID, plan.Demo)
		if err != nil {
			return run.Invocation{}, "", false, err
		}
		// A single-feature command returns a report with only that feature set,
		// so it decodes as an analysis.
		return inv, "analysis", false, nil

	case cli.ActionWorkflow:
		inv, err := run.Workflow(binary, plan.Workflow, plan.Image, plan.Query, plan.Demo)
		if err != nil {
			return run.Invocation{}, "", false, err
		}
		return inv, plan.Workflow, false, nil

	case cli.ActionShowcase:
		return run.Showcase(binary, plan.Demo), "showcase", false, nil

	case cli.ActionGallery:
		// gallery and config print for humans: pass their output through.
		return run.Gallery(binary), "gallery", true, nil

	case cli.ActionConfig:
		return run.Config(binary, plan.Demo, ""), "config", true, nil
	}

	return run.Invocation{}, "", false, fmt.Errorf("unknown action %q", plan.Action)
}

// plainBody renders an unstyled summary of a JSON payload.
func plainBody(kind string, raw []byte) (string, error) {
	data, err := ExtractJSON(raw)
	if err != nil {
		// Not everything is JSON (config prints a panel); show what came back.
		return strings.TrimRight(stripANSI(string(raw)), "\n"), nil
	}

	switch kind {
	case "analysis":
		analysis, err := report.Decode[report.Analysis](data)
		if err != nil {
			return "", err
		}
		return PlainAnalysis(analysis), nil

	case "comparison":
		comparison, err := report.Decode[report.Comparison](data)
		if err != nil {
			return "", err
		}
		return PlainComparison(comparison), nil

	case "showcase":
		showcase, err := report.Decode[report.Showcase](data)
		if err != nil {
			return "", err
		}
		return PlainShowcase(showcase), nil

	default:
		// Workflows already print a compact JSON document, which is the most
		// useful plain rendering of them.
		return string(data), nil
	}
}

// PlainAnalysis renders an analysis without styling.
func PlainAnalysis(analysis report.Analysis) string {
	var out strings.Builder

	out.WriteString("image: " + analysis.ImagePath + "\n")
	out.WriteString("features: " + JoinOrDash(analysis.AvailableFeatures) + "\n")
	for _, insight := range analysis.Insights {
		out.WriteString("insight: " + insight + "\n")
	}

	if analysis.Classification != nil {
		out.WriteString("\nclassification (" + analysis.Classification.ModelVersion + ")\n")
		for _, label := range analysis.Classification.Labels {
			out.WriteString(fmt.Sprintf("  %-32s %s\n", label.Name, FormatPct(label.ConfidencePct)))
		}
	}
	if analysis.Detection != nil {
		out.WriteString("\nobjects (" + analysis.Detection.ModelVersion + ")\n")
		for _, object := range analysis.Detection.Objects {
			out.WriteString(fmt.Sprintf("  %-24s %8s  center %s\n",
				object.Name, FormatPct(object.ConfidencePct), CenterLabel(object.BoundingPolygon)))
		}
	}
	if analysis.Text != nil {
		out.WriteString("\ntext\n")
		for _, line := range analysis.Text.Lines {
			out.WriteString(fmt.Sprintf("  %-40s %s\n", line.Text, FormatPct(line.Confidence*100)))
		}
	}
	if analysis.Faces != nil {
		out.WriteString("\nfaces\n")
		for i, face := range analysis.Faces.Faces {
			out.WriteString(fmt.Sprintf("  face %d  %s  %d landmark(s)\n",
				i+1, FormatPct(face.Confidence*100), len(face.Landmarks)))
		}
	}
	if analysis.Document != nil {
		out.WriteString(fmt.Sprintf("\ndocument: %d page(s), %d field(s), %d table(s)\n",
			analysis.Document.PageCount, len(analysis.Document.Fields), len(analysis.Document.Tables)))
		for _, field := range analysis.Document.Fields {
			out.WriteString(fmt.Sprintf("  %-24s %-20s %s\n",
				field.Label, field.Value, FormatPct(field.Confidence*100)))
		}
	}
	return strings.TrimRight(out.String(), "\n")
}

// PlainComparison renders a comparison without styling.
func PlainComparison(comparison report.Comparison) string {
	var out strings.Builder

	out.WriteString("left:  " + comparison.LeftImage + "\n")
	out.WriteString("right: " + comparison.RightImage + "\n")
	out.WriteString("shared features: " + JoinOrDash(comparison.SharedFeatures) + "\n")
	out.WriteString("left only: " + JoinOrDash(comparison.LeftOnlyFeatures) + "\n")
	out.WriteString("right only: " + JoinOrDash(comparison.RightOnlyFeatures) + "\n")
	out.WriteString("top label: " + comparison.TopLabelChange.Left + " -> " +
		comparison.TopLabelChange.Right + "\n")
	out.WriteString("object count change: " + FormatDelta(comparison.ObjectCountDelta) + "\n")
	out.WriteString("ocr line change: " + FormatDelta(comparison.OCRLineDelta) + "\n")
	out.WriteString("face count change: " + FormatDelta(comparison.FaceCountDelta) + "\n")
	out.WriteString("document field change: " + FormatDelta(comparison.DocumentFieldDelta) + "\n")

	if len(comparison.ObjectDeltas) > 0 {
		out.WriteString("\nobject changes\n")
		for _, delta := range comparison.ObjectDeltas {
			out.WriteString(fmt.Sprintf("  %-24s %4d -> %4d  %s\n",
				delta.Name, delta.Left, delta.Right, FormatDelta(delta.Delta)))
		}
	}
	return strings.TrimRight(out.String(), "\n")
}

// PlainShowcase renders a showcase snapshot without styling.
func PlainShowcase(showcase report.Showcase) string {
	var out strings.Builder

	out.WriteString("generated: " + showcase.GeneratedAt + "\n")
	out.WriteString("assets: " + strconv.Itoa(showcase.AssetCount) + "\n")
	out.WriteString("workflows: " + strconv.Itoa(showcase.WorkflowCount) + "\n")
	out.WriteString("comparisons: " + strconv.Itoa(showcase.ComparisonCount) + "\n")
	for _, headline := range showcase.Headlines {
		out.WriteString("headline: " + headline + "\n")
	}
	for _, asset := range showcase.Gallery {
		out.WriteString(fmt.Sprintf("\n%s\n  top label %s, %d object(s), %d OCR line(s)\n",
			asset.Filename, asset.Summary.TopLabel, asset.Summary.ObjectCount, asset.Summary.OCRLineCount))
	}
	return strings.TrimRight(out.String(), "\n")
}
