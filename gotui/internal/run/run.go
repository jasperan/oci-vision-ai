// Package run builds the argv for invoking the real oci-vision CLI.
//
// The subcommand and flag spellings here are taken from
// src/oci_vision/cli/app.py and cross-checked against `oci-vision <cmd> --help`.
// Nothing is guessed.
//
// No credential ever reaches argv: demo mode needs none, and live mode reads the
// OCI config file through the SDK exactly as the Python CLI does. This front-end
// therefore never handles a private key, and argv is safe to show in a process
// list, a log, or the TUI.
package run

import (
	"fmt"
	"sort"
	"strings"
)

// Features are the five vision features, in the order cli/app.py documents them.
var Features = []string{"classification", "detection", "text", "faces", "document"}

// WorkflowKinds are the workflow packs in src/oci_vision/workflows.
var WorkflowKinds = []string{"receipt", "shelf", "inspection", "archive-search"}

// Invocation is a ready-to-exec subprocess call.
type Invocation struct {
	Argv []string
}

// CommandLine renders argv for display.
func (i Invocation) CommandLine() string { return strings.Join(i.Argv, " ") }

// ValidateFeatureNames rejects anything the CLI would reject with a typer
// BadParameter, so the user sees the reason in the form instead of as a failed
// subprocess.
func ValidateFeatureNames(features []string) error {
	for _, feature := range features {
		if !IsFeature(feature) {
			return fmt.Errorf("unsupported feature %q; valid choices: %s",
				feature, strings.Join(Features, ", "))
		}
	}
	return nil
}

// IsFeature reports whether name is one of the five vision features.
func IsFeature(name string) bool {
	for _, feature := range Features {
		if feature == name {
			return true
		}
	}
	return false
}

// IsWorkflowKind reports whether kind is one of the workflow packs.
func IsWorkflowKind(kind string) bool {
	for _, candidate := range WorkflowKinds {
		if candidate == kind {
			return true
		}
	}
	return false
}

// ValidateWorkflowKind rejects an unknown workflow before it is run.
func ValidateWorkflowKind(kind string) error {
	if !IsWorkflowKind(kind) {
		return fmt.Errorf("unsupported workflow %q; valid choices: %s",
			kind, strings.Join(WorkflowKinds, ", "))
	}
	return nil
}

// ParseFeatureList splits a comma-separated --features value.
//
// An empty value means "all", which is what the CLI's own default does.
func ParseFeatureList(raw string) []string {
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

// SortedKeys returns a map's keys in a stable order, so a rendered table does
// not shuffle between redraws.
func SortedKeys[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

// jsonOut appends the machine-readable output selector. Every read command this
// front-end runs asks for JSON: the Go side renders it, so no Rich table ever
// has to be parsed.
func jsonOut(argv []string) []string {
	return append(argv, "--output-format", "json")
}

// demoFlag appends --demo when demo mode is on.
func demoFlag(argv []string, demo bool) []string {
	if demo {
		return append(argv, "--demo")
	}
	return argv
}

// Analyze builds `oci-vision analyze IMAGE [--features ...] [--model-id ID] --output-format json`.
func Analyze(binary, image string, features []string, modelID string, demo bool) Invocation {
	argv := []string{binary, "analyze", image}
	if len(features) > 0 {
		argv = append(argv, "--features", strings.Join(features, ","))
	}
	if modelID != "" {
		argv = append(argv, "--model-id", modelID)
	}
	return Invocation{Argv: jsonOut(demoFlag(argv, demo))}
}

// Compare builds `oci-vision compare LEFT RIGHT [--features ...] --output-format json`.
func Compare(binary, left, right string, features []string, demo bool) Invocation {
	argv := []string{binary, "compare", left, right}
	if len(features) > 0 {
		argv = append(argv, "--features", strings.Join(features, ","))
	}
	return Invocation{Argv: jsonOut(demoFlag(argv, demo))}
}

// Batch builds `oci-vision batch IMAGE... [--features ...] --output-format json`.
func Batch(binary string, images []string, features []string, demo bool) Invocation {
	argv := append([]string{binary, "batch"}, images...)
	if len(features) > 0 {
		argv = append(argv, "--features", strings.Join(features, ","))
	}
	return Invocation{Argv: jsonOut(demoFlag(argv, demo))}
}

// Feature builds a single-feature command: classify, detect, ocr, faces or document.
//
// The CLI names two of these differently from the feature ("detect" for
// detection, "ocr" for text), so the mapping is explicit rather than derived.
func Feature(binary, feature, image, modelID string, demo bool) (Invocation, error) {
	command, ok := featureCommands[feature]
	if !ok {
		return Invocation{}, fmt.Errorf("no CLI command for feature %q", feature)
	}
	argv := []string{binary, command, image}
	// Only classify and detect accept --model-id (cli/app.py).
	if modelID != "" && (feature == "classification" || feature == "detection") {
		argv = append(argv, "--model-id", modelID)
	}
	return Invocation{Argv: jsonOut(demoFlag(argv, demo))}, nil
}

// featureCommands maps a feature name to the CLI subcommand that runs it alone.
var featureCommands = map[string]string{
	"classification": "classify",
	"detection":      "detect",
	"text":           "ocr",
	"faces":          "faces",
	"document":       "document",
}

// Workflow builds `oci-vision workflow KIND IMAGE [--query Q]`.
//
// The workflow command prints JSON natively (it dumps the summary dict), so no
// --output-format is passed.
func Workflow(binary, kind, image, query string, demo bool) (Invocation, error) {
	if err := ValidateWorkflowKind(kind); err != nil {
		return Invocation{}, err
	}
	argv := []string{binary, "workflow", kind, image}
	// Only archive-search declares a use for the query (cli/app.py accepts the flag
	// on every kind but ignores it elsewhere), so it is sent only where it means
	// something and argv stays an honest description of what will run.
	if kind == "archive-search" {
		if strings.TrimSpace(query) == "" {
			return Invocation{}, fmt.Errorf("archive-search needs a query")
		}
		argv = append(argv, "--query", query)
	}
	return Invocation{Argv: demoFlag(argv, demo)}, nil
}

// Showcase builds `oci-vision showcase --output-format json`.
func Showcase(binary string, demo bool) Invocation {
	return Invocation{Argv: jsonOut(demoFlag([]string{binary, "showcase"}, demo))}
}

// Gallery builds `oci-vision gallery`.
//
// The command prints a Rich table, so this is only used for the pass-through
// path where the CLI's own rendering is what the user asked to see.
func Gallery(binary string) Invocation {
	return Invocation{Argv: []string{binary, "gallery"}}
}

// Config builds `oci-vision config [--demo] [--profile NAME]`.
func Config(binary string, demo bool, profile string) Invocation {
	argv := []string{binary, "config"}
	if profile != "" {
		argv = append(argv, "--profile", profile)
	}
	return Invocation{Argv: demoFlag(argv, demo)}
}
