package cli

import (
	"strings"
	"testing"
)

// TestResolvePrecedence pins the "most specific flag wins" rule, so a read-only
// flag can never silently mask an action the user actually asked for.
func TestResolvePrecedence(t *testing.T) {
	cases := []struct {
		name string
		opts Options
		want string
	}{
		{"gallery wins over everything", Options{GalleryFlag: true, Image: "a.png", ShowcaseFlag: true}, ActionGallery},
		{"config beats an image", Options{ConfigFlag: true, Image: "a.png"}, ActionConfig},
		{"compare beats an image", Options{Left: "a.png", Right: "b.png", Image: "c.png"}, ActionCompare},
		{"workflow beats a bare image", Options{Workflow: "receipt", Image: "a.png"}, ActionWorkflow},
		{"feature beats a bare image", Options{Feature: "classification", Image: "a.png"}, ActionFeature},
		{"showcase stands alone", Options{ShowcaseFlag: true}, ActionShowcase},
		{"a bare image analyses", Options{Image: "a.png"}, ActionAnalyze},
	}

	for _, c := range cases {
		plan, err := Resolve(c.opts)
		if err != nil {
			t.Fatalf("%s: Resolve: %v", c.name, err)
		}
		if plan.Action != c.want {
			t.Errorf("%s: action = %q, want %q", c.name, plan.Action, c.want)
		}
	}
}

// TestResolveNeverPrompts is the contract of the non-interactive path: with nothing
// to do it reports usage rather than waiting for input.
func TestResolveNeverPrompts(t *testing.T) {
	_, err := Resolve(Options{})
	if err == nil {
		t.Fatal("empty options must be refused")
	}
	message := err.Error()
	for _, want := range []string{"--image", "--workflow", "--showcase", "--gallery", "--config"} {
		if !strings.Contains(message, want) {
			t.Errorf("usage message should mention %q, got %q", want, message)
		}
	}
}

func TestResolveRejectsHalfAComparison(t *testing.T) {
	if _, err := Resolve(Options{Left: "a.png"}); err == nil {
		t.Fatal("a comparison with one side must be refused")
	}
	if _, err := Resolve(Options{Right: "b.png"}); err == nil {
		t.Fatal("a comparison with one side must be refused")
	}
}

func TestResolveRejectsUnknownFeatureAndWorkflow(t *testing.T) {
	if _, err := Resolve(Options{Feature: "vibes", Image: "a.png"}); err == nil {
		t.Fatal("an unsupported feature must be refused")
	}
	if _, err := Resolve(Options{Workflow: "laundry", Image: "a.png"}); err == nil {
		t.Fatal("an unsupported workflow must be refused")
	}
}

// TestResolveArchiveSearchNeedsAQuery keeps the CLI's own requirement enforced
// before a subprocess is spawned.
func TestResolveArchiveSearchNeedsAQuery(t *testing.T) {
	if _, err := Resolve(Options{Workflow: "archive-search", Image: "a.png"}); err == nil {
		t.Fatal("archive-search without a query must be refused")
	}
	plan, err := Resolve(Options{Workflow: "archive-search", Image: "a.png", Query: "INV-1001"})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if plan.Query != "INV-1001" {
		t.Errorf("Query = %q", plan.Query)
	}
}

func TestResolveRequiresAnImageForImageActions(t *testing.T) {
	if _, err := Resolve(Options{Workflow: "receipt"}); err == nil {
		t.Fatal("a workflow without an image must be refused")
	}
	if _, err := Resolve(Options{Feature: "classification"}); err == nil {
		t.Fatal("a feature run without an image must be refused")
	}
}

// TestDemoIsTheDefault pins the repo's stated convention (CLAUDE.md: demo mode is
// the default entry point), so the UI never demands OCI credentials to start.
func TestDemoIsTheDefault(t *testing.T) {
	plan, err := Resolve(Options{Image: "dog_closeup.jpg"})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if !plan.Demo {
		t.Error("demo mode should be the default")
	}

	live, err := Resolve(Options{Image: "dog_closeup.jpg", Live: true})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if live.Demo {
		t.Error("--live should turn demo mode off")
	}
}

// TestDemoBeatsLiveWhenBothAreGiven keeps the outcome deterministic rather than
// dependent on flag order.
func TestDemoBeatsLiveWhenBothAreGiven(t *testing.T) {
	plan, err := Resolve(Options{Image: "a.png", Live: true, Demo: true})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if plan.Demo {
		t.Error("--live is the explicit opt-out and must win")
	}
}

func TestResolveCarriesFeaturesAndModelID(t *testing.T) {
	plan, err := Resolve(Options{
		Image:    "a.png",
		Features: "classification,detection",
		ModelID:  "ocid1.vision.oc1..abc",
	})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if len(plan.Features) != 2 || plan.Features[1] != "detection" {
		t.Errorf("Features = %v", plan.Features)
	}
	if plan.ModelID != "ocid1.vision.oc1..abc" {
		t.Errorf("ModelID = %q", plan.ModelID)
	}
}

func TestResolveRejectsAnInvalidFeatureList(t *testing.T) {
	if _, err := Resolve(Options{Image: "a.png", Features: "classification,nonsense"}); err == nil {
		t.Fatal("an unsupported feature in the list must be refused")
	}
}

// TestResolveTrimsWhitespace keeps a shell-quoted value from reaching argv with
// stray spaces.
func TestResolveTrimsWhitespace(t *testing.T) {
	plan, err := Resolve(Options{Image: "  dog_closeup.jpg  ", Left: "  a.png ", Right: " b.png  "})
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if plan.Action != ActionCompare {
		t.Fatalf("action = %q", plan.Action)
	}
	if plan.Left != "a.png" || plan.Right != "b.png" {
		t.Errorf("Left = %q, Right = %q", plan.Left, plan.Right)
	}
}
