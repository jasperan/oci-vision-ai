// Package cli resolves the non-interactive path: flags and environment decide
// everything, with no terminal involved.
//
// This is the path a cron job, a CI step or a piped shell takes, so it must never
// depend on a prompt being answerable.
package cli

import (
	"fmt"
	"strings"

	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// Actions the front-end can be asked to perform without a terminal.
const (
	ActionAnalyze  = "analyze"
	ActionCompare  = "compare"
	ActionFeature  = "feature"
	ActionWorkflow = "workflow"
	ActionShowcase = "showcase"
	ActionGallery  = "gallery"
	ActionConfig   = "config"
)

// Options are the flags the front-end accepts.
type Options struct {
	Image    string
	Features string
	ModelID  string
	Feature  string
	Workflow string
	Query    string
	Left     string
	Right    string

	GalleryFlag  bool
	ConfigFlag   bool
	ShowcaseFlag bool

	// Demo and Live are the two halves of one choice. Demo is the default
	// (CLAUDE.md: demo mode is the default entry point and needs no credentials),
	// so Live exists to opt out rather than Demo existing to opt in.
	Demo bool
	Live bool
}

// Plan is a fully resolved non-interactive decision.
type Plan struct {
	Action   string
	Image    string
	Left     string
	Right    string
	Feature  string
	Workflow string
	Query    string
	ModelID  string
	Features []string
	Demo     bool
}

// Resolve turns flags into a Plan, or reports exactly which flag is missing.
//
// It never reads stdin.
func Resolve(o Options) (Plan, error) {
	features := run.ParseFeatureList(o.Features)
	if err := run.ValidateFeatureNames(features); err != nil {
		return Plan{}, err
	}

	plan := Plan{
		Features: features,
		ModelID:  strings.TrimSpace(o.ModelID),
		Demo:     !o.Live,
	}

	switch {
	case o.GalleryFlag:
		plan.Action = ActionGallery

	case o.ConfigFlag:
		plan.Action = ActionConfig

	case strings.TrimSpace(o.Left) != "" || strings.TrimSpace(o.Right) != "":
		if strings.TrimSpace(o.Left) == "" || strings.TrimSpace(o.Right) == "" {
			return Plan{}, fmt.Errorf("compare needs two images: --left <image> --right <image>")
		}
		plan.Action = ActionCompare
		plan.Left, plan.Right = strings.TrimSpace(o.Left), strings.TrimSpace(o.Right)

	case strings.TrimSpace(o.Workflow) != "":
		kind := strings.TrimSpace(o.Workflow)
		if err := run.ValidateWorkflowKind(kind); err != nil {
			return Plan{}, err
		}
		if kind == "archive-search" && strings.TrimSpace(o.Query) == "" {
			return Plan{}, fmt.Errorf("workflow archive-search needs --query")
		}
		if strings.TrimSpace(o.Image) == "" {
			return Plan{}, fmt.Errorf("workflow %s needs --image", kind)
		}
		plan.Action = ActionWorkflow
		plan.Workflow, plan.Query, plan.Image = kind, o.Query, strings.TrimSpace(o.Image)

	case strings.TrimSpace(o.Feature) != "":
		feature := strings.TrimSpace(o.Feature)
		if !run.IsFeature(feature) {
			return Plan{}, fmt.Errorf("unsupported feature %q; valid choices: %s",
				feature, strings.Join(run.Features, ", "))
		}
		if strings.TrimSpace(o.Image) == "" {
			return Plan{}, fmt.Errorf("feature %s needs --image", feature)
		}
		plan.Action = ActionFeature
		plan.Feature, plan.Image = feature, strings.TrimSpace(o.Image)

	case o.ShowcaseFlag:
		plan.Action = ActionShowcase

	case strings.TrimSpace(o.Image) != "":
		plan.Action = ActionAnalyze
		plan.Image = strings.TrimSpace(o.Image)

	default:
		return Plan{}, fmt.Errorf(
			"no terminal on stdin: pass an action flag such as --image <image>, " +
				"--feature classify --image <image>, --workflow receipt --image <image>, " +
				"--compare-left <a> --compare-right <b>, --showcase, --gallery or --config")
	}

	return plan, nil
}
