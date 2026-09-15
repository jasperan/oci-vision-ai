package tui

import (
	"errors"
	"path"
	"strings"

	"charm.land/huh/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/gallery"
	"github.com/jasperan/oci-vision-ai/gotui/internal/huhstyle"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// Actions shared by the TUI and the plain path.
const (
	ActionAnalyze  = "analyze"
	ActionCompare  = "compare"
	ActionWorkflow = "workflow"
	ActionShowcase = "showcase"
	ActionGallery  = "gallery"
	ActionConfig   = "config"

	ActionAgain = "again"
	ActionBack  = "back"
	ActionQuit  = "quit"
)

// MenuActions are the top-level destinations, in the order cli/app.py documents
// its command groups.
var MenuActions = []huh.Option[string]{
	huh.NewOption("Analyze an image", ActionAnalyze),
	huh.NewOption("Compare two images", ActionCompare),
	huh.NewOption("Run a workflow pack", ActionWorkflow),
	huh.NewOption("Showcase snapshot", ActionShowcase),
	huh.NewOption("Demo gallery", ActionGallery),
	huh.NewOption("Configuration check", ActionConfig),
	huh.NewOption("Quit", ActionQuit),
}

// MenuAnswers is the menu selection.
type MenuAnswers struct{ Choice string }

// menuFields are the menu's questions.
func menuFields(choice *string, projectRoot string) []huh.Field {
	description := "Demo mode needs no OCI credentials."
	if projectRoot == "" {
		description = "Repo root not found, so the gallery picker is unavailable and a path must be typed. " + description
	}
	return []huh.Field{
		huh.NewSelect[string]().
			Title("What next?").
			Description(description).
			Options(MenuActions...).
			Value(choice),
	}
}

// MenuForm builds the main menu.
func MenuForm(choice *string, projectRoot string) *huh.Form {
	return themed(huh.NewForm(
		huh.NewGroup(menuFields(choice, projectRoot)...).Title("oci-vision"),
	))
}

// ImageOptions builds the gallery picker's options.
//
// A fresh slice is built per load: huh silently ignores an empty Options call, so
// a single reused slice could not be refreshed.
//
// The value is the FILENAME, not the id, because demo mode resolves a bare
// filename against the bundled assets and the CLI's own gallery table documents
// filenames.
func ImageOptions(entries []gallery.Entry) []huh.Option[string] {
	if len(entries) == 0 {
		return nil
	}
	options := make([]huh.Option[string], 0, len(entries))
	for _, entry := range entries {
		options = append(options, huh.NewOption(entry.Label(), entry.Filename))
	}
	return options
}

// FeatureOptions builds the multi-select's options from run.Features.
func FeatureOptions() []huh.Option[string] {
	options := make([]huh.Option[string], 0, len(run.Features))
	for _, feature := range run.Features {
		options = append(options, huh.NewOption(feature, feature))
	}
	return options
}

// optionalText is an input that never blocks submission.
//
// It exists for accessible mode: a huh screen-reader prompt substitutes a field's
// default only AFTER its validator has run, and never prints that default, so a
// validator that rejects "" traps a user on a question whose answer they cannot
// see. Every genuinely optional field is therefore exempt from blank rejection,
// and the requirement it represents is enforced once, after the form completes, by
// ValidateImageRequired / ValidateWorkflow / ValidateComparePairs.
func optionalText(title, description, placeholder string, value *string) huh.Field {
	return huh.NewInput().
		Title(title).
		Description(description).
		Placeholder(placeholder).
		Value(value).
		Validate(func(string) error { return nil })
}

// AnalyzeAnswers are the analyze form's values.
type AnalyzeAnswers struct {
	// Asset is the chosen gallery filename.
	Asset string
	// ImagePath, when set, overrides Asset. Two fields rather than a hidden
	// conditional screen keeps the picker usable for the bundled assets while
	// still allowing any path in live mode, and both descriptions state which
	// one wins.
	ImagePath string
	Features  []string
	Demo      bool
	ModelID   string
}

// Image resolves the image the CLI should be given.
//
// A typed path wins over the picker.
func (a AnalyzeAnswers) Image() string {
	if trimmed := strings.TrimSpace(a.ImagePath); trimmed != "" {
		return trimmed
	}
	return strings.TrimSpace(a.Asset)
}

// AnalyzeSeed pre-fills the form from flags, so a user who already knows their
// target does not retype it. The form still validates everything.
type AnalyzeSeed struct {
	Image     string
	ImagePath string
	Features  []string
	Live      bool
	ModelID   string
}

// AnalyzeDefaults seeds the analyze form: demo mode on (CLAUDE.md makes demo the
// default entry point) and every feature selected (the CLI's own "all" default).
//
// A seeded image that is NOT one of the gallery assets is placed in ImagePath
// rather than Asset. That matters: a huh Select whose Value is not among its
// Options silently falls back to the first option on submit, so seeding a plain
// path into Asset made `--image missing.png` analyse dog_closeup.jpg instead.
func AnalyzeDefaults(seed AnalyzeSeed, entries []gallery.Entry) AnalyzeAnswers {
	features := seed.Features
	if len(features) == 0 {
		features = append(features, run.Features...)
	}

	answers := AnalyzeAnswers{
		Features: features,
		Demo:     !seed.Live,
		ModelID:  seed.ModelID,
	}
	answers.Asset, answers.ImagePath = seedImage(seed.Image, seed.ImagePath, entries)
	return answers
}

// seedImage routes a seeded image to the field that can actually hold it.
func seedImage(image, imagePath string, entries []gallery.Entry) (asset, path string) {
	path = strings.TrimSpace(imagePath)
	image = strings.TrimSpace(image)
	if image == "" {
		return "", path
	}
	if filename, ok := MatchGalleryEntry(entries, image); ok {
		return filename, path
	}
	if path != "" {
		// An explicit path already wins; the gallery value would be ignored anyway.
		return "", path
	}
	return "", image
}

// MatchGalleryEntry resolves a user-supplied image against the gallery manifest by
// filename OR by id, which is how oci_vision.core.demo resolves a demo asset.
func MatchGalleryEntry(entries []gallery.Entry, image string) (string, bool) {
	needle := strings.TrimSpace(image)
	if needle == "" {
		return "", false
	}
	base := path.Base(needle)
	stem := strings.TrimSuffix(base, path.Ext(base))
	for _, entry := range entries {
		if needle == entry.Filename || base == entry.Filename || stem == entry.ID || needle == entry.ID {
			return entry.Filename, true
		}
	}
	return "", false
}

// modeField is the demo/live choice, phrased as a question rather than a flag.
func modeField(demo *bool, description string) huh.Field {
	return huh.NewConfirm().
		Title("Run in demo mode?").
		Description(description).
		Affirmative("Demo (offline)").
		Negative("Live (needs OCI config)").
		Value(demo)
}

// analyzeFields are the analyze questions.
//
// They are separated from AnalyzeForm so the accessibility tests can drive a real
// field rather than re-declaring it, which is what pins the actual wiring.
func analyzeFields(answers *AnalyzeAnswers, entries []gallery.Entry) []huh.Field {
	fields := []huh.Field{}

	if options := ImageOptions(entries); options != nil {
		if answers.Asset == "" {
			answers.Asset = entries[0].Filename
		}
		fields = append(fields, huh.NewSelect[string]().
			Title("Gallery asset").
			Description("Bundled demo images. Ignored when a path is given below.").
			Options(options...).
			Value(&answers.Asset))
	}

	return append(fields,
		optionalText("Image path (optional)",
			"Overrides the gallery asset. Needed in live mode when no asset is shown.",
			"path/to/image.jpg", &answers.ImagePath),

		huh.NewMultiSelect[string]().
			Title("Features").
			Description("The five vision features. Clear all to run every feature the image supports.").
			Options(FeatureOptions()...).
			Value(&answers.Features),

		optionalText("Custom model OCID (optional)",
			"Only used by classification and detection.",
			"ocid1.vision.oc1..", &answers.ModelID),

		modeField(&answers.Demo, "Demo mode needs no OCI credentials and never calls OCI."),
	)
}

// AnalyzeForm builds the analyze form.
//
// One group: huh's accessible path runs only a form's FIRST group, so a
// multi-group form would silently never ask the later questions.
func AnalyzeForm(answers *AnalyzeAnswers, entries []gallery.Entry) *huh.Form {
	return themed(huh.NewForm(
		huh.NewGroup(analyzeFields(answers, entries)...).Title("Analyze"),
	))
}

// ValidateImageRequired reports whether a usable image was chosen.
//
// It runs after the form completes rather than inside a field validator, because
// which of the two image fields is authoritative depends on both.
func ValidateImageRequired(answers AnalyzeAnswers) error {
	if answers.Image() == "" {
		return errors.New("choose a gallery asset or type an image path")
	}
	return nil
}

// CompareAnswers are the compare form's values.
type CompareAnswers struct {
	Left      string
	Right     string
	LeftPath  string
	RightPath string
	Features  []string
	Demo      bool
}

// LeftImage and RightImage resolve each side, a typed path winning over the picker.
func (a CompareAnswers) LeftImage() string  { return resolvePair(a.LeftPath, a.Left) }
func (a CompareAnswers) RightImage() string { return resolvePair(a.RightPath, a.Right) }

func resolvePair(path, asset string) string {
	if trimmed := strings.TrimSpace(path); trimmed != "" {
		return trimmed
	}
	return strings.TrimSpace(asset)
}

// compareFields are the compare questions.
func compareFields(answers *CompareAnswers, entries []gallery.Entry) []huh.Field {
	fields := []huh.Field{}

	if options := ImageOptions(entries); options != nil {
		if answers.Left == "" {
			answers.Left = entries[0].Filename
		}
		if answers.Right == "" {
			answers.Right = entries[min(1, len(entries)-1)].Filename
		}
		fields = append(fields,
			huh.NewSelect[string]().
				Title("Left image").
				Options(options...).
				Value(&answers.Left),
			huh.NewSelect[string]().
				Title("Right image").
				Options(options...).
				Value(&answers.Right))
	}

	return append(fields,
		optionalText("Left path (optional)", "Overrides the left gallery asset.", "", &answers.LeftPath),
		optionalText("Right path (optional)", "Overrides the right gallery asset.", "", &answers.RightPath),

		huh.NewMultiSelect[string]().
			Title("Features").
			Description("Leave empty to compare every feature the images support.").
			Options(FeatureOptions()...).
			Value(&answers.Features),

		modeField(&answers.Demo, "Demo mode needs no OCI credentials."),
	)
}

// CompareForm builds the compare form.
func CompareForm(answers *CompareAnswers, entries []gallery.Entry) *huh.Form {
	return themed(huh.NewForm(
		huh.NewGroup(compareFields(answers, entries)...).Title("Compare"),
	))
}

// ValidateComparePairs checks both sides were given.
func ValidateComparePairs(answers CompareAnswers) error {
	if answers.LeftImage() == "" || answers.RightImage() == "" {
		return errors.New("compare needs both a left and a right image")
	}
	return nil
}

// WorkflowAnswers are the workflow form's values.
type WorkflowAnswers struct {
	Kind string
	// Asset is the chosen gallery filename; ImagePath overrides it.
	Asset     string
	ImagePath string
	Query     string
	Demo      bool
}

// Image resolves the image the workflow should run against.
func (a WorkflowAnswers) Image() string {
	if trimmed := strings.TrimSpace(a.ImagePath); trimmed != "" {
		return trimmed
	}
	return strings.TrimSpace(a.Asset)
}

// WorkflowOptions builds the workflow kind options.
func WorkflowOptions() []huh.Option[string] {
	labels := map[string]string{
		"receipt":        "Receipt - extract invoice fields",
		"shelf":          "Shelf audit - count objects on shelves",
		"inspection":     "Inspection - classify, detect and read text",
		"archive-search": "Archive search - find a value across images",
	}
	options := make([]huh.Option[string], 0, len(run.WorkflowKinds))
	for _, kind := range run.WorkflowKinds {
		options = append(options, huh.NewOption(labels[kind], kind))
	}
	return options
}

// workflowFields are the workflow questions.
func workflowFields(answers *WorkflowAnswers, entries []gallery.Entry) []huh.Field {
	if answers.Kind == "" {
		answers.Kind = run.WorkflowKinds[0]
	}
	fields := []huh.Field{
		huh.NewSelect[string]().
			Title("Workflow").
			Options(WorkflowOptions()...).
			Value(&answers.Kind),
	}

	if options := ImageOptions(entries); options != nil {
		if answers.Asset == "" {
			answers.Asset = entries[0].Filename
		}
		fields = append(fields, huh.NewSelect[string]().
			Title("Gallery asset").
			Description("Ignored when a path is given below.").
			Options(options...).
			Value(&answers.Asset))
	}

	return append(fields,
		optionalText("Image path (optional)", "Overrides the gallery asset.", "", &answers.ImagePath),
		optionalText("Query (archive-search only)",
			"Required by archive-search, ignored by the other workflows.", "INV-1001", &answers.Query),
		modeField(&answers.Demo, "Demo mode needs no OCI credentials."),
	)
}

// WorkflowForm builds the workflow form.
func WorkflowForm(answers *WorkflowAnswers, entries []gallery.Entry) *huh.Form {
	return themed(huh.NewForm(
		huh.NewGroup(workflowFields(answers, entries)...).Title("Workflow"),
	))
}

// ValidateWorkflow checks the workflow can actually be run.
//
// The archive-search query rule is enforced here as well as in run.Workflow, so
// the user is told in the form instead of by a failed subprocess.
func ValidateWorkflow(answers WorkflowAnswers) error {
	if err := run.ValidateWorkflowKind(answers.Kind); err != nil {
		return err
	}
	if answers.Image() == "" {
		return errors.New("choose a gallery asset or type an image path")
	}
	if answers.Kind == "archive-search" && strings.TrimSpace(answers.Query) == "" {
		return errors.New("archive-search needs a query")
	}
	return nil
}

// ConfigAnswers are the configuration check's values.
type ConfigAnswers struct {
	Demo    bool
	Profile string
}

// configFields are the configuration questions.
func configFields(answers *ConfigAnswers) []huh.Field {
	return []huh.Field{
		huh.NewConfirm().
			Title("Check demo mode or live credentials?").
			Description("Demo mode always succeeds. Live mode validates the OCI config file.").
			Affirmative("Demo").
			Negative("Live").
			Value(&answers.Demo),

		optionalText("OCI profile (optional)",
			"Passed as --profile; ignored in demo mode.", "DEFAULT", &answers.Profile),
	}
}

// ConfigForm builds the configuration-check form.
func ConfigForm(answers *ConfigAnswers) *huh.Form {
	return themed(huh.NewForm(
		huh.NewGroup(configFields(answers)...).Title("Configuration"),
	))
}

// themed attaches the project theme, the accessibility flag and an explicit
// keymap.
//
// The keymap is not optional: a bare huh field has none, so keystrokes would be
// silently ignored.
func themed(form *huh.Form) *huh.Form {
	return form.
		WithTheme(huh.ThemeFunc(huhstyle.Theme)).
		WithAccessible(huhstyle.Accessible()).
		WithKeyMap(huh.NewDefaultKeyMap())
}

// ValidateDefaulted accepts an empty answer as "keep the value already in the field".
//
// It exists for accessible mode. huh's screen-reader path runs a field's validator
// on the raw line and only afterwards substitutes the field's default
// (internal/accessibility/accessibility.go:PromptString returns
// cmp.Or(strings.TrimSpace(input), defaultValue)), and it never prints that
// default. A pre-filled field whose validator rejects "" therefore keeps
// re-prompting on a bare Enter, so a screen-reader user cannot accept a value they
// cannot see.
func ValidateDefaulted(inner func(string) error) func(string) error {
	return func(s string) error {
		if strings.TrimSpace(s) == "" {
			return nil
		}
		return inner(s)
	}
}
