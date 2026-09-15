package run

import (
	"strings"
	"testing"
)

// These tests pin the exact argv the real CLI is given. The flag spellings come
// from src/oci_vision/cli/app.py, so a rename there must fail here rather than
// silently producing a command the CLI rejects.

func TestAnalyzeBuildsTheDocumentedFlags(t *testing.T) {
	inv := Analyze("oci-vision", "dog_closeup.jpg", []string{"classification", "detection"}, "", true)
	want := "oci-vision analyze dog_closeup.jpg --features classification,detection --demo --output-format json"
	if got := inv.CommandLine(); got != want {
		t.Fatalf("argv = %q, want %q", got, want)
	}
}

// TestAnalyzeOmitsFeaturesWhenNoneChosen pins the "all" default: cli/app.py treats
// an absent --features as every feature, so passing an empty list must not send
// "--features" with nothing after it.
func TestAnalyzeOmitsFeaturesWhenNoneChosen(t *testing.T) {
	inv := Analyze("oci-vision", "dog_closeup.jpg", nil, "", true)
	for _, arg := range inv.Argv {
		if arg == "--features" {
			t.Fatalf("an empty feature list must not send --features: %v", inv.Argv)
		}
	}
	if inv.CommandLine() != "oci-vision analyze dog_closeup.jpg --demo --output-format json" {
		t.Fatalf("unexpected argv: %v", inv.Argv)
	}
}

func TestAnalyzeIncludesModelID(t *testing.T) {
	inv := Analyze("oci-vision", "img.png", nil, "ocid1.vision.oc1..abc", false)
	joined := inv.CommandLine()
	if !strings.Contains(joined, "--model-id ocid1.vision.oc1..abc") {
		t.Fatalf("model id missing from %q", joined)
	}
	if strings.Contains(joined, "--demo") {
		t.Fatalf("live mode must not pass --demo: %q", joined)
	}
}

func TestCompareArgOrderIsLeftThenRight(t *testing.T) {
	inv := Compare("oci-vision", "left.png", "right.png", nil, true)
	want := "oci-vision compare left.png right.png --demo --output-format json"
	if got := inv.CommandLine(); got != want {
		t.Fatalf("argv = %q, want %q", got, want)
	}
}

// TestFeatureCommandNamesAreTheCliSpellings is the mapping that cannot be derived:
// the CLI calls the text feature "ocr" and the detection feature "detect".
func TestFeatureCommandNamesAreTheCliSpellings(t *testing.T) {
	cases := map[string]string{
		"classification": "classify",
		"detection":      "detect",
		"text":           "ocr",
		"faces":          "faces",
		"document":       "document",
	}
	for feature, command := range cases {
		inv, err := Feature("oci-vision", feature, "img.png", "", true)
		if err != nil {
			t.Fatalf("feature %q: %v", feature, err)
		}
		if inv.Argv[1] != command {
			t.Errorf("feature %q mapped to %q, want %q", feature, inv.Argv[1], command)
		}
	}
}

// TestFeatureRejectsModelIDOnUnsupportedCommands pins cli/app.py: only classify and
// detect declare --model-id, so sending it elsewhere would be an unknown-option
// failure at runtime.
func TestFeatureRejectsModelIDOnUnsupportedCommands(t *testing.T) {
	for _, feature := range []string{"text", "faces", "document"} {
		inv, err := Feature("oci-vision", feature, "img.png", "ocid1.vision.oc1..abc", true)
		if err != nil {
			t.Fatalf("feature %q: %v", feature, err)
		}
		if strings.Contains(inv.CommandLine(), "--model-id") {
			t.Errorf("feature %q must not receive --model-id: %v", feature, inv.Argv)
		}
	}
	for _, feature := range []string{"classification", "detection"} {
		inv, err := Feature("oci-vision", feature, "img.png", "ocid1.vision.oc1..abc", true)
		if err != nil {
			t.Fatalf("feature %q: %v", feature, err)
		}
		if !strings.Contains(inv.CommandLine(), "--model-id") {
			t.Errorf("feature %q should receive --model-id: %v", feature, inv.Argv)
		}
	}
}

func TestFeatureRejectsAnUnknownFeature(t *testing.T) {
	if _, err := Feature("oci-vision", "telepathy", "img.png", "", true); err == nil {
		t.Fatal("expected an error for an unsupported feature")
	}
}

func TestWorkflowArchiveSearchRequiresAQuery(t *testing.T) {
	if _, err := Workflow("oci-vision", "archive-search", "a.png", "", true); err == nil {
		t.Fatal("archive-search without a query must be refused before it runs")
	}
	inv, err := Workflow("oci-vision", "archive-search", "a.png", "INV-1001", true)
	if err != nil {
		t.Fatalf("archive-search with a query: %v", err)
	}
	if !strings.Contains(inv.CommandLine(), "--query INV-1001") {
		t.Fatalf("query missing from %q", inv.CommandLine())
	}
}

// TestWorkflowOmitsQueryForOtherKinds keeps the flag from reaching a workflow that
// does not declare it.
func TestWorkflowOmitsQueryForOtherKinds(t *testing.T) {
	inv, err := Workflow("oci-vision", "receipt", "invoice_demo.png", "ignored", true)
	if err != nil {
		t.Fatalf("receipt: %v", err)
	}
	if strings.Contains(inv.CommandLine(), "--query") {
		t.Fatalf("receipt must not receive --query: %v", inv.Argv)
	}
}

func TestWorkflowRejectsUnknownKind(t *testing.T) {
	if _, err := Workflow("oci-vision", "laundry", "a.png", "", true); err == nil {
		t.Fatal("an unsupported workflow must be refused")
	}
}

// TestWorkflowCarriesNoOutputFormat pins that the workflow command prints JSON
// natively, so no --output-format may be added.
func TestWorkflowCarriesNoOutputFormat(t *testing.T) {
	inv, err := Workflow("oci-vision", "shelf", "dog_closeup.jpg", "", true)
	if err != nil {
		t.Fatalf("shelf: %v", err)
	}
	if strings.Contains(inv.CommandLine(), "--output-format") {
		t.Fatalf("workflow must not receive --output-format: %v", inv.Argv)
	}
}

func TestParseFeatureList(t *testing.T) {
	cases := []struct {
		in   string
		want []string
	}{
		{"", nil},
		{"   ", nil},
		{"classification", []string{"classification"}},
		{"classification,detection", []string{"classification", "detection"}},
		{" classification , detection ", []string{"classification", "detection"}},
		{",,", nil},
	}
	for _, c := range cases {
		got := ParseFeatureList(c.in)
		if len(got) != len(c.want) {
			t.Fatalf("ParseFeatureList(%q) = %v, want %v", c.in, got, c.want)
		}
		for i := range got {
			if got[i] != c.want[i] {
				t.Fatalf("ParseFeatureList(%q) = %v, want %v", c.in, got, c.want)
			}
		}
	}
}

func TestValidateFeatureNames(t *testing.T) {
	if err := ValidateFeatureNames([]string{"classification", "document"}); err != nil {
		t.Fatalf("valid features rejected: %v", err)
	}
	if err := ValidateFeatureNames([]string{"classification", "vibes"}); err == nil {
		t.Fatal("an unsupported feature must be rejected")
	}
}

// TestSortedKeysIsStable is what keeps a rendered table from shuffling between
// redraws.
func TestSortedKeysIsStable(t *testing.T) {
	counts := map[string]int{"Dog": 5, "Bull": 1, "Car": 2}
	for i := 0; i < 12; i++ {
		got := SortedKeys(counts)
		want := []string{"Bull", "Car", "Dog"}
		for j := range want {
			if got[j] != want[j] {
				t.Fatalf("iteration %d: SortedKeys = %v, want %v", i, got, want)
			}
		}
	}
}

func TestConfigFlags(t *testing.T) {
	if got := Config("oci-vision", true, "").CommandLine(); got != "oci-vision config --demo" {
		t.Fatalf("argv = %q", got)
	}
	if got := Config("oci-vision", false, "DEFAULT").CommandLine(); got != "oci-vision config --profile DEFAULT" {
		t.Fatalf("argv = %q", got)
	}
}

// TestNoCredentialEverReachesArgv is the safety property: demo mode needs none, and
// live mode reads the OCI config file through the SDK, so no secret may appear in a
// command line that is shown in the UI or visible in `ps`.
func TestNoCredentialEverReachesArgv(t *testing.T) {
	invocations := []Invocation{
		Analyze("oci-vision", "img.png", nil, "", true),
		Compare("oci-vision", "a.png", "b.png", nil, true),
		Showcase("oci-vision", true),
		Config("oci-vision", true, ""),
	}
	for _, inv := range invocations {
		joined := strings.ToLower(inv.CommandLine())
		for _, forbidden := range []string{"password", "tenancy", "fingerprint", "private-key", "secret"} {
			if strings.Contains(joined, forbidden) {
				t.Errorf("argv %q contains %q", joined, forbidden)
			}
		}
	}
}
