package tui

import (
	"bytes"
	"errors"
	"strings"
	"testing"

	"charm.land/huh/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/gallery"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// This file covers the accessible half of the form contract.
//
// Why it exists: huh's accessible prompts run a field's validator on the raw line
// and only afterwards substitute the field's default, and they never print that
// default. A pre-filled field whose validator rejects "" therefore re-prompts on
// every bare Enter, so a screen-reader user cannot accept a value they cannot see.
//
// Two consequences are pinned here:
//  1. no optional field may reject a blank answer, and
//  2. the requirement it represents must still be enforced, once, after the form
//     completes.
//
// Field.RunAccessible is used rather than Form.Run because each accessible prompt
// builds its own buffered scanner over the reader, so only the first prompt of a
// multi-field form can be fed a real answer; per-field driving is the only way to
// exercise the rest.

var errBlank = errors.New("blank answer rejected")

// runFieldAccessible drives one real field, built by the module's own field
// builder, through huh's accessible path with a single blank line.
func runFieldAccessible(t *testing.T, field huh.Field, input string) string {
	t.Helper()
	var out bytes.Buffer
	if err := field.RunAccessible(&out, strings.NewReader(input)); err != nil {
		// A field whose echo mode needs a tty reports here; the form ignores it too.
		t.Logf("RunAccessible returned %v (ignored, as huh.Form does)", err)
	}
	return out.String()
}

// TestValidateDefaultedAcceptsBlank is the unit half of the fix.
func TestValidateDefaultedAcceptsBlank(t *testing.T) {
	inner := func(s string) error {
		if strings.TrimSpace(s) == "" {
			return errBlank
		}
		if s == "bad" {
			return errors.New("not usable")
		}
		return nil
	}
	wrapped := ValidateDefaulted(inner)

	for _, in := range []string{"", "   ", "\t"} {
		if err := wrapped(in); err != nil {
			t.Errorf("ValidateDefaulted(inner)(%q) = %v, want nil", in, err)
		}
	}
	if err := wrapped("bad"); err == nil {
		t.Error(`ValidateDefaulted(inner)("bad") = nil, want the inner validator's error`)
	}
	if err := wrapped("8000"); err != nil {
		t.Errorf(`ValidateDefaulted(inner)("8000") = %v, want nil`, err)
	}
}

// TestOptionalFieldsAcceptABlankAnswer drives the real analyze and workflow fields,
// which are the ones a screen-reader user must be able to skip.
func TestOptionalFieldsAcceptABlankAnswer(t *testing.T) {
	entries := []gallery.Entry{{ID: "dog_closeup", Filename: "dog_closeup.jpg"}}

	t.Run("analyze image path", func(t *testing.T) {
		answers := AnalyzeDefaults(AnalyzeSeed{}, entries)
		fields := analyzeFields(&answers, entries)

		// The field index depends on whether the picker was built, so find it by
		// running every field: a rejection would name itself in the output.
		for _, field := range fields {
			out := runFieldAccessible(t, field, "\n")
			if strings.Contains(out, "cannot be empty") || strings.Contains(out, "required") {
				t.Errorf("an optional analyze field rejected a blank answer, so a screen-reader "+
					"user is trapped:\n%s", out)
			}
		}
	})

	t.Run("workflow query and path", func(t *testing.T) {
		answers := WorkflowAnswers{Kind: "receipt"}
		fields := workflowFields(&answers, entries)

		for _, field := range fields {
			out := runFieldAccessible(t, field, "\n")
			// The query is only required by archive-search, and this form is a
			// receipt run, so blank must be accepted here.
			if strings.Contains(out, "archive-search needs a query") {
				t.Errorf("the receipt workflow rejected a blank query:\n%s", out)
			}
		}
	})

	t.Run("config profile", func(t *testing.T) {
		answers := ConfigAnswers{Demo: true}
		for _, field := range configFields(&answers) {
			out := runFieldAccessible(t, field, "\n")
			if strings.Contains(out, "cannot be empty") {
				t.Errorf("the optional OCI profile rejected a blank answer:\n%s", out)
			}
		}
	})
}

// TestRequirementsAreEnforcedAfterTheForm is the other half: relaxing the field
// validators must not lose the requirement. Each is checked directly, which is
// where the regression risk actually sits.
func TestRequirementsAreEnforcedAfterTheForm(t *testing.T) {
	t.Run("analyze needs an image", func(t *testing.T) {
		if err := ValidateImageRequired(AnalyzeAnswers{}); err == nil {
			t.Error("an analysis with no image must be refused")
		}
		if err := ValidateImageRequired(AnalyzeAnswers{Asset: "dog_closeup.jpg"}); err != nil {
			t.Errorf("a chosen asset should satisfy the requirement: %v", err)
		}
		if err := ValidateImageRequired(AnalyzeAnswers{ImagePath: "/tmp/custom.png"}); err != nil {
			t.Errorf("a typed path should satisfy the requirement: %v", err)
		}
		if err := ValidateImageRequired(AnalyzeAnswers{Asset: "   "}); err == nil {
			t.Error("a whitespace-only asset must not satisfy the requirement")
		}
	})

	t.Run("compare needs both sides", func(t *testing.T) {
		if err := ValidateComparePairs(CompareAnswers{Left: "a.png"}); err == nil {
			t.Error("a one-sided comparison must be refused")
		}
		if err := ValidateComparePairs(CompareAnswers{Left: "a.png", Right: "b.png"}); err != nil {
			t.Errorf("a two-sided comparison should pass: %v", err)
		}
		if err := ValidateComparePairs(CompareAnswers{LeftPath: "a.png", RightPath: "b.png"}); err != nil {
			t.Errorf("typed paths should satisfy the requirement: %v", err)
		}
	})

	t.Run("archive-search needs a query", func(t *testing.T) {
		answers := WorkflowAnswers{Kind: "archive-search", Asset: "invoice_demo.png"}
		if err := ValidateWorkflow(answers); err == nil {
			t.Error("archive-search without a query must be refused")
		}
		answers.Query = "INV-1001"
		if err := ValidateWorkflow(answers); err != nil {
			t.Errorf("archive-search with a query should pass: %v", err)
		}
	})

	t.Run("workflow needs an image", func(t *testing.T) {
		if err := ValidateWorkflow(WorkflowAnswers{Kind: "receipt"}); err == nil {
			t.Error("a workflow with no image must be refused")
		}
	})

	t.Run("unknown workflow kind", func(t *testing.T) {
		if err := ValidateWorkflow(WorkflowAnswers{Kind: "laundry", Asset: "a.png"}); err == nil {
			t.Error("an unsupported workflow must be refused")
		}
	})
}

// TestTypedPathBeatsThePicker pins the documented precedence for both forms that
// have a picker.
func TestTypedPathBeatsThePicker(t *testing.T) {
	if got := (AnalyzeAnswers{Asset: "asset.png", ImagePath: "/tmp/path.png"}).Image(); got != "/tmp/path.png" {
		t.Errorf("Image() = %q, want the typed path", got)
	}
	if got := (AnalyzeAnswers{Asset: "asset.png"}).Image(); got != "asset.png" {
		t.Errorf("Image() = %q, want the picker value", got)
	}
	if got := (WorkflowAnswers{Asset: "asset.png", ImagePath: "/tmp/path.png"}).Image(); got != "/tmp/path.png" {
		t.Errorf("Image() = %q, want the typed path", got)
	}
	if got := (CompareAnswers{Left: "a.png", LeftPath: " /tmp/a.png "}).LeftImage(); got != "/tmp/a.png" {
		t.Errorf("LeftImage() = %q, want the trimmed typed path", got)
	}
}

// TestDefaultsAreDemoAndAllFeatures pins the two seeding decisions the header and
// the CLI invocation both depend on.
func TestDefaultsAreDemoAndAllFeatures(t *testing.T) {
	answers := AnalyzeDefaults(AnalyzeSeed{}, nil)
	if !answers.Demo {
		t.Error("demo mode should be the default")
	}
	if len(answers.Features) != len(run.Features) {
		t.Errorf("features = %v, want all %d", answers.Features, len(run.Features))
	}

	live := AnalyzeDefaults(AnalyzeSeed{Live: true}, nil)
	if live.Demo {
		t.Error("--live should turn demo mode off in the seeded form")
	}
}

// TestPickerSeedsFromTheManifest pins that the first asset is preselected, so the
// form is completable with a bare Enter.
func TestPickerSeedsFromTheManifest(t *testing.T) {
	entries := []gallery.Entry{
		{ID: "dog_closeup", Filename: "dog_closeup.jpg"},
		{ID: "sign_board", Filename: "sign_board.png"},
	}

	analyze := AnalyzeAnswers{}
	analyzeFields(&analyze, entries)
	if analyze.Asset != "dog_closeup.jpg" {
		t.Errorf("analyze asset = %q, want the first entry", analyze.Asset)
	}

	compare := CompareAnswers{}
	compareFields(&compare, entries)
	if compare.Left != "dog_closeup.jpg" || compare.Right != "sign_board.png" {
		t.Errorf("compare seeds = %q/%q, want the first two entries", compare.Left, compare.Right)
	}

	workflow := WorkflowAnswers{}
	workflowFields(&workflow, entries)
	if workflow.Asset != "dog_closeup.jpg" {
		t.Errorf("workflow asset = %q, want the first entry", workflow.Asset)
	}
	if workflow.Kind != run.WorkflowKinds[0] {
		t.Errorf("workflow kind = %q, want the first kind", workflow.Kind)
	}
}

// TestPairsSeedEvenWithASingleEntry guards the index arithmetic in the compare
// picker, which must not panic on a one-image manifest.
func TestPairsSeedEvenWithASingleEntry(t *testing.T) {
	entries := []gallery.Entry{{ID: "only", Filename: "only.png"}}
	answers := CompareAnswers{}
	compareFields(&answers, entries)
	if answers.Left != "only.png" || answers.Right != "only.png" {
		t.Errorf("seeds = %q/%q, want the single entry on both sides", answers.Left, answers.Right)
	}
}

// TestFormsBuildWithoutAPicker keeps the fallback usable: with no manifest the
// analyze form must still be completable, just with a typed path.
func TestFormsBuildWithoutAPicker(t *testing.T) {
	analyze := AnalyzeAnswers{}
	if form := AnalyzeForm(&analyze, nil); form == nil {
		t.Fatal("the analyze form must build with no gallery entries")
	}
	// With no picker the asset stays empty, so the path is the only route, which
	// the post-form validation reports.
	if err := ValidateImageRequired(analyze); err == nil {
		t.Error("with no picker and no path, the requirement must still fire")
	}
	if err := ValidateImageRequired(AnalyzeAnswers{ImagePath: "/tmp/x.png"}); err != nil {
		t.Errorf("a typed path should satisfy it with no picker: %v", err)
	}
}

// TestImageOptionsUseFilenames pins the value sent to the CLI, which resolves
// gallery assets by filename in demo mode.
func TestImageOptionsUseFilenames(t *testing.T) {
	entries := []gallery.Entry{{ID: "dog_closeup", Filename: "dog_closeup.jpg", Description: "A dog"}}
	options := ImageOptions(entries)
	if len(options) != 1 {
		t.Fatalf("options = %d, want 1", len(options))
	}
	if got := options[0].Value; got != "dog_closeup.jpg" {
		t.Errorf("option value = %q, want the filename", got)
	}
}

func TestFeatureOptionsCoverEveryFeature(t *testing.T) {
	options := FeatureOptions()
	if len(options) != len(run.Features) {
		t.Fatalf("options = %d, want %d", len(options), len(run.Features))
	}
	for i, feature := range run.Features {
		if options[i].Value != feature {
			t.Errorf("option %d = %q, want %q", i, options[i].Value, feature)
		}
	}
}
