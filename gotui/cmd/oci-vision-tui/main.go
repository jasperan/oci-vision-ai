// Command oci-vision-tui is a Go front-end for the oci-vision Python CLI.
//
// It is an ADDITIONAL way to run the same engine, not a replacement: every result
// it shows was produced by shelling out to the installed `oci-vision` binary over
// the interface that binary already exposes ("--output-format json" for the
// feature commands, and its native JSON for the workflow command). Nothing about
// image analysis is reimplemented here, so a Go user and a Python user get
// identical numbers.
//
// Two paths:
//   - a terminal: a huh-driven menu (analyze, compare, workflow, showcase,
//     gallery, config) with the results rendered in a scrollable panel
//   - no terminal: flags only, never a prompt
//
// Demo mode is the default, matching CLAUDE.md ("demo mode is the default entry
// point"): the UI therefore never requires OCI credentials, and --live opts out.
package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	tea "charm.land/bubbletea/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/cli"
	"github.com/jasperan/oci-vision-ai/gotui/internal/gallery"
	"github.com/jasperan/oci-vision-ai/gotui/internal/huhstyle"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
	"github.com/jasperan/oci-vision-ai/gotui/internal/tui"
)

const version = "0.1.0"

func main() {
	os.Exit(realMain())
}

func realMain() int {
	var (
		opts    cli.Options
		binary  = flag.String("bin", "oci-vision", "path to the oci-vision CLI")
		timeout = flag.Duration("timeout", tui.DefaultTimeout, "subprocess timeout")
		jsonOut = flag.Bool("json", false, "print the CLI's JSON document unchanged (implies the non-interactive path)")
		plain   = flag.Bool("plain", false, "never open the full-screen UI")
		list    = flag.Bool("list-features", false, "print the available features and workflows, then exit")
		ver     = flag.Bool("version", false, "print the front-end version, then exit")
	)
	flag.StringVar(&opts.Image, "image", "", "image path or gallery filename to analyse")
	flag.StringVar(&opts.Features, "features", "", "comma-separated features: "+joinFeatures())
	flag.StringVar(&opts.Feature, "feature", "", "run one feature only (see -list-features)")
	flag.StringVar(&opts.ModelID, "model-id", "", "OCI custom model OCID (classification and detection)")
	flag.StringVar(&opts.Workflow, "workflow", "", "workflow pack: receipt, shelf, inspection, archive-search")
	flag.StringVar(&opts.Query, "query", "", "query for the archive-search workflow")
	flag.StringVar(&opts.Left, "compare-left", "", "left image for a comparison")
	flag.StringVar(&opts.Right, "compare-right", "", "right image for a comparison")
	flag.BoolVar(&opts.ShowcaseFlag, "showcase", false, "print the showcase snapshot")
	flag.BoolVar(&opts.GalleryFlag, "gallery", false, "print the demo gallery")
	flag.BoolVar(&opts.ConfigFlag, "config", false, "print the configuration check")
	flag.BoolVar(&opts.Live, "live", false, "use live OCI credentials instead of demo mode")
	flag.Parse()

	if *ver {
		fmt.Printf("oci-vision-tui %s\n", version)
		return 0
	}

	if *list {
		fmt.Println("features: " + joinFeatures())
		fmt.Println("workflows: " + joinWorkflows())
		return 0
	}

	projectRoot := gallery.FindProjectRoot()
	entries, entriesErr := gallery.Load(projectRoot)
	if entriesErr != nil && huhstyle.Interactive() && !*plain {
		// The picker would be empty, which is worth saying once. It is not fatal:
		// the analyze form falls back to a typed path.
		fmt.Fprintf(os.Stderr,
			"note: %v\nnote: the gallery picker is unavailable; type an image path instead\n", entriesErr)
	}

	// --- screen-reader path ------------------------------------------------------
	// huh's accessible rendering only exists in its standalone Run path, so the
	// embedded full-screen UI is skipped entirely here.
	if huhstyle.Accessible() {
		fmt.Fprintln(os.Stdout, tui.AccessibleNotice)
		return runPlain(opts, *jsonOut, projectRoot, *binary, *timeout)
	}

	// --- non-interactive path ----------------------------------------------------
	if !huhstyle.Interactive() || *plain || *jsonOut {
		return runPlain(opts, *jsonOut, projectRoot, *binary, *timeout)
	}

	// --- full-screen path --------------------------------------------------------
	model := tui.New(tui.Options{
		ProjectRoot: projectRoot,
		Entries:     entries,
		Exec:        tui.ShellExec{Dir: projectRoot},
		Binary:      *binary,
		Timeout:     *timeout,
		Seed:        seedFromOptions(opts),
	})
	if _, err := tea.NewProgram(model).Run(); err != nil {
		fmt.Fprintf(os.Stderr, "oci-vision-tui: %v\n", err)
		return 1
	}
	return 0
}

// runPlain resolves flags with no terminal at all.
func runPlain(opts cli.Options, jsonOut bool, projectRoot, binary string, timeout time.Duration) int {
	plan, err := cli.Resolve(opts)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 2
	}
	err = tui.RunPlan(plan, tui.PlainOptions{
		Exec:    tui.ShellExec{Dir: projectRoot},
		Binary:  binary,
		Timeout: timeout,
		Out:     os.Stdout,
		JSON:    jsonOut,
	})
	if err != nil {
		return 1
	}
	return 0
}

// seedFromOptions pre-fills the wizard from the flags, so a user who already knows
// their target does not retype it. The wizard still validates everything.
func seedFromOptions(o cli.Options) tui.AnalyzeSeed {
	return tui.AnalyzeSeed{
		Image:    o.Image,
		Features: run.ParseFeatureList(o.Features),
		Live:     o.Live,
		ModelID:  o.ModelID,
	}
}

func joinFeatures() string { return join(run.Features) }

func joinWorkflows() string { return join(run.WorkflowKinds) }

func join(values []string) string {
	out := ""
	for i, value := range values {
		if i > 0 {
			out += ", "
		}
		out += value
	}
	return out
}
