package tui

import (
	"bytes"
	"errors"
	"strings"
	"testing"
	"time"

	"charm.land/lipgloss/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/cli"
	"github.com/jasperan/oci-vision-ai/gotui/internal/report"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

func testPlainOptions(exec Executor) PlainOptions {
	return PlainOptions{Exec: exec, Binary: "oci-vision", Timeout: time.Second, Out: &bytes.Buffer{}}
}

// TestRunPlanPrintsAPlainSummary is the non-interactive contract: a pipe gets
// readable text, with the same numbers the TUI would show.
func TestRunPlanPrintsAPlainSummary(t *testing.T) {
	exec := &stubExec{raw: []byte(analysisFixture)}
	opts := testPlainOptions(exec)

	if err := RunPlan(cli.Plan{Action: cli.ActionAnalyze, Image: "dog_closeup.jpg", Demo: true}, opts); err != nil {
		t.Fatalf("RunPlan: %v", err)
	}

	out := opts.Out.(*bytes.Buffer).String()
	for _, want := range []string{"image: dog_closeup.jpg", "Dog", "99.2%", "insight: Top label: Dog (99.2%)"} {
		if !strings.Contains(out, want) {
			t.Fatalf("plain output is missing %q:\n%s", want, out)
		}
	}
	// The plain path must not leak lipgloss escape codes into a pipe.
	if strings.Contains(out, "\x1b[") {
		t.Fatalf("plain output contains ANSI escapes:\n%q", out)
	}
}

// TestRunPlanJSONIsTheCliDocumentUnchanged is what makes the path scriptable: the
// tag must not reformat or re-encode anything.
func TestRunPlanJSONIsTheCliDocumentUnchanged(t *testing.T) {
	exec := &stubExec{raw: []byte(analysisFixture)}
	opts := testPlainOptions(exec)
	opts.JSON = true

	if err := RunPlan(cli.Plan{Action: cli.ActionAnalyze, Image: "dog_closeup.jpg", Demo: true}, opts); err != nil {
		t.Fatalf("RunPlan: %v", err)
	}

	out := strings.TrimSpace(opts.Out.(*bytes.Buffer).String())
	if !strings.Contains(out, `"image_path": "dog_closeup.jpg"`) {
		t.Fatalf("JSON output was reformatted:\n%s", out)
	}
	if !strings.HasPrefix(out, "{") {
		t.Fatalf("JSON output does not start with the document:\n%s", out)
	}
}

// TestRunPlanPassesThroughSelfRenderingCommands covers gallery and config: their
// output is drawn for humans, so only colour codes may be removed.
func TestRunPlanPassesThroughSelfRenderingCommands(t *testing.T) {
	rich := "\x1b[36m╭─ Demo Gallery ─╮\x1b[0m\n│ dog_closeup.jpg │\n"
	exec := &stubExec{raw: []byte(rich)}
	opts := testPlainOptions(exec)

	if err := RunPlan(cli.Plan{Action: cli.ActionGallery}, opts); err != nil {
		t.Fatalf("RunPlan: %v", err)
	}

	out := opts.Out.(*bytes.Buffer).String()
	if !strings.Contains(out, "dog_closeup.jpg") {
		t.Fatalf("gallery output lost its content:\n%s", out)
	}
	if strings.Contains(out, "\x1b[") {
		t.Fatalf("colour codes were not stripped:\n%q", out)
	}
}

// TestRunPlanFailureNamesTheCommand keeps a broken run reproducible from the error
// alone.
func TestRunPlanFailureNamesTheCommand(t *testing.T) {
	exec := &stubExec{err: errors.New("Error: Demo asset not found: missing.png")}
	opts := testPlainOptions(exec)

	err := RunPlan(cli.Plan{Action: cli.ActionAnalyze, Image: "missing.png", Demo: true}, opts)
	if err == nil {
		t.Fatal("a failed run must be reported")
	}

	out := opts.Out.(*bytes.Buffer).String()
	for _, want := range []string{"Demo asset not found", "$ oci-vision analyze missing.png"} {
		if !strings.Contains(out, want) {
			t.Fatalf("failure output is missing %q:\n%s", want, out)
		}
	}
}

// TestRunPlanSelectsTheRightInvocation covers the plan-to-argv mapping, including
// the single-feature commands.
func TestRunPlanSelectsTheRightInvocation(t *testing.T) {
	cases := []struct {
		plan cli.Plan
		want string
	}{
		{cli.Plan{Action: cli.ActionAnalyze, Image: "a.png", Features: []string{"text"}, Demo: true},
			"oci-vision analyze a.png --features text --demo --output-format json"},
		{cli.Plan{Action: cli.ActionCompare, Left: "a.png", Right: "b.png", Demo: true},
			"oci-vision compare a.png b.png --demo --output-format json"},
		{cli.Plan{Action: cli.ActionFeature, Feature: "text", Image: "a.png", Demo: true},
			"oci-vision ocr a.png --demo --output-format json"},
		{cli.Plan{Action: cli.ActionWorkflow, Workflow: "receipt", Image: "a.png", Demo: true},
			"oci-vision workflow receipt a.png --demo"},
		{cli.Plan{Action: cli.ActionShowcase, Demo: true},
			"oci-vision showcase --demo --output-format json"},
		{cli.Plan{Action: cli.ActionGallery}, "oci-vision gallery"},
		{cli.Plan{Action: cli.ActionConfig, Demo: true}, "oci-vision config --demo"},
	}

	for _, c := range cases {
		exec := &stubExec{raw: []byte(`{}`)}
		opts := testPlainOptions(exec)
		if err := RunPlan(c.plan, opts); err != nil {
			t.Fatalf("action %q: RunPlan: %v", c.plan.Action, err)
		}
		if got := exec.got.CommandLine(); got != c.want {
			t.Errorf("action %q: argv = %q, want %q", c.plan.Action, got, c.want)
		}
	}
}

// TestRunPlanRefusesAnUnknownAction keeps a programming error from spawning a
// subprocess.
func TestRunPlanRefusesAnUnknownAction(t *testing.T) {
	exec := &stubExec{}
	opts := testPlainOptions(exec)
	if err := RunPlan(cli.Plan{Action: "teleport"}, opts); err == nil {
		t.Fatal("an unknown action must be refused")
	}
	if exec.got.Argv != nil {
		t.Fatalf("no subprocess may run for an unknown action: %v", exec.got.Argv)
	}
}

// --- renderers ---------------------------------------------------------------------

func TestPlainAnalysisNamesEveryFeaturePresent(t *testing.T) {
	analysis, err := report.Decode[report.Analysis]([]byte(analysisFixture))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	out := PlainAnalysis(analysis)

	for _, want := range []string{"classification (1.5.97)", "objects (1.3.557)", "Dog"} {
		if !strings.Contains(out, want) {
			t.Fatalf("plain analysis is missing %q:\n%s", want, out)
		}
	}
	// A feature the payload did not include must not appear at all.
	for _, unwanted := range []string{"\nfaces", "\ntext\n", "\ndocument"} {
		if strings.Contains(out, unwanted) {
			t.Fatalf("plain analysis rendered %q for an absent feature:\n%s", unwanted, out)
		}
	}
}

func TestPlainComparisonKeepsSigns(t *testing.T) {
	comparison, err := report.Decode[report.Comparison]([]byte(`{
      "left_image": "a.png", "right_image": "b.png",
      "shared_features": [], "left_only_features": ["detection"], "right_only_features": [],
      "top_label_change": {"left": "Dog", "right": "-", "changed": true},
      "object_count_delta": -11, "object_deltas": [{"name": "Dog", "left": 5, "right": 0, "delta": -5}],
      "ocr_similarity": null, "ocr_line_delta": 2, "face_count_delta": 0,
      "document_field_delta": 0, "document_field_changes": [],
      "left_summary": {}, "right_summary": {}}`))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	out := PlainComparison(comparison)

	if !strings.Contains(out, "object count change: -11") {
		t.Fatalf("a negative delta lost its sign:\n%s", out)
	}
	if !strings.Contains(out, "ocr line change: +2") {
		t.Fatalf("a positive delta lost its sign:\n%s", out)
	}
	if !strings.Contains(out, "Dog -> -") {
		t.Fatalf("the top-label change is missing:\n%s", out)
	}
}

func TestPlainShowcaseListsHeadlinesAndAssets(t *testing.T) {
	showcase, err := report.Decode[report.Showcase]([]byte(`{
      "generated_at": "now", "demo": true, "asset_count": 4, "workflow_count": 4,
      "comparison_count": 2, "gallery": [{"id": "a", "filename": "dog_closeup.jpg",
        "description": "", "recommended_features": [], "command": "", "insights": [],
        "summary": {"image": "dog_closeup.jpg", "features": [], "feature_count": 1,
          "top_label": "Dog", "top_confidence_pct": 99.25, "object_count": 11,
          "object_counts": {}, "ocr_line_count": 0, "ocr_preview": "", "face_count": 0,
          "document_field_count": 0, "document_fields": {}, "document_table_count": 0,
          "elapsed_seconds": 0}}],
      "batch": {}, "comparisons": [], "workflows": {}, "commands": {},
      "headlines": ["4 curated demo assets cover 5 vision feature(s)."]}`))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	out := PlainShowcase(showcase)

	for _, want := range []string{"assets: 4", "headline: 4 curated", "dog_closeup.jpg", "top label Dog"} {
		if !strings.Contains(out, want) {
			t.Fatalf("plain showcase is missing %q:\n%s", want, out)
		}
	}
}

// --- JSON extraction ---------------------------------------------------------------

// TestExtractJSONToleratesLeadingNoise makes the decode survive a warning line a
// future CLI release might print before the document.
func TestExtractJSONToleratesLeadingNoise(t *testing.T) {
	raw := []byte("warning: something\n{\"a\": 1}\n")
	got, err := ExtractJSON(raw)
	if err != nil {
		t.Fatalf("ExtractJSON: %v", err)
	}
	if string(got) != `{"a": 1}` {
		t.Fatalf("ExtractJSON = %q", got)
	}
}

func TestExtractJSONStripsColourCodes(t *testing.T) {
	got, err := ExtractJSON([]byte("\x1b[32m{\"a\": 1}\x1b[0m"))
	if err != nil {
		t.Fatalf("ExtractJSON: %v", err)
	}
	if string(got) != `{"a": 1}` {
		t.Fatalf("ExtractJSON = %q", got)
	}
}

func TestExtractJSONAcceptsATopLevelArray(t *testing.T) {
	got, err := ExtractJSON([]byte(`[{"a": 1}]`))
	if err != nil {
		t.Fatalf("ExtractJSON: %v", err)
	}
	if string(got) != `[{"a": 1}]` {
		t.Fatalf("ExtractJSON = %q", got)
	}
}

// TestExtractJSONReportsNoDocument is the error path a broken CLI takes.
func TestExtractJSONReportsNoDocument(t *testing.T) {
	if _, err := ExtractJSON([]byte("total failure")); err == nil {
		t.Fatal("missing JSON must be reported")
	}
}

// --- executor error reporting ------------------------------------------------------

// TestBestErrorLinePrefersTheCliOwnMessage covers the Rich-rendered failure, which
// arrives box-drawn and coloured.
func TestBestErrorLinePrefersTheCliOwnMessage(t *testing.T) {
	stderr := "\x1b[31m╭─────────────────────╮\x1b[0m\n" +
		"\x1b[31m│ Error: Demo asset not found: x.png │\x1b[0m\n" +
		"\x1b[31m╰─────────────────────╯\x1b[0m\n"

	got := bestErrorLine(stderr, "")
	if !strings.Contains(got, "Demo asset not found") {
		t.Fatalf("bestErrorLine = %q, want the CLI's own message", got)
	}
	if strings.Contains(got, "│") || strings.Contains(got, "\x1b[") {
		t.Fatalf("bestErrorLine left decoration in %q", got)
	}
}

// TestBestErrorLineIgnoresABareExitStatus keeps "exit status 1" from being the
// reported reason when the CLI said something better.
func TestBestErrorLineIgnoresABareExitStatus(t *testing.T) {
	if got := bestErrorLine("", "exit status 1"); got != "exit status 1" {
		t.Fatalf("bestErrorLine = %q, want the only line available", got)
	}
	if got := bestErrorLine("", "│╰──╯"); got != "" {
		t.Fatalf("bestErrorLine = %q, want empty for decoration only", got)
	}
}

// TestShellExecReportsAMissingBinary keeps a wrong -bin from looking like a crash.
func TestShellExecReportsAMissingBinary(t *testing.T) {
	_, err := (ShellExec{}).Run(run.Invocation{Argv: []string{"definitely-not-a-binary-xyz"}}, time.Second)
	if err == nil {
		t.Fatal("a missing binary must be reported")
	}
	if !strings.Contains(err.Error(), "not found on PATH") {
		t.Fatalf("error = %q, want it to name the PATH problem", err)
	}
}

func TestShellExecRejectsAnEmptyInvocation(t *testing.T) {
	if _, err := (ShellExec{}).Run(run.Invocation{}, time.Second); err == nil {
		t.Fatal("an empty invocation must be refused")
	}
}

// --- formatting helpers ------------------------------------------------------------

func TestTruncateIsDisplayWidthAware(t *testing.T) {
	// "日本" is 4 columns wide but 2 runes, so a rune-count truncation would
	// overflow the pane it was measured against.
	got := Truncate("日本語", 3)
	if width := lipgloss.Width(got); width > 3 {
		t.Fatalf("Truncate produced %d columns, want <= 3: %q", width, got)
	}
	if strings.Contains(Truncate("short", 10), "~") {
		t.Error("a string that fits must not be truncated")
	}
}

func TestFormatDeltaKeepsTheSign(t *testing.T) {
	if got := FormatDelta(3); got != "+3" {
		t.Errorf("FormatDelta(3) = %q, want +3", got)
	}
	if got := FormatDelta(-3); got != "-3" {
		t.Errorf("FormatDelta(-3) = %q, want -3", got)
	}
	if got := FormatDelta(0); got != "0" {
		t.Errorf("FormatDelta(0) = %q, want 0", got)
	}
}

func TestJoinOrDashAndDerefOrDash(t *testing.T) {
	if got := JoinOrDash(nil); got != "-" {
		t.Errorf("JoinOrDash(nil) = %q, want -", got)
	}
	if got := JoinOrDash([]string{"a", "b"}); got != "a, b" {
		t.Errorf("JoinOrDash = %q", got)
	}
	if got := DerefOrDash(nil); got != "-" {
		t.Errorf("DerefOrDash(nil) = %q, want -", got)
	}
	value := "x"
	if got := DerefOrDash(&value); got != "x" {
		t.Errorf("DerefOrDash = %q", got)
	}
}
