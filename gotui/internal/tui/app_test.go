package tui

import (
	"errors"
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"
	"charm.land/huh/v2"
	"charm.land/lipgloss/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/gallery"
	"github.com/jasperan/oci-vision-ai/gotui/internal/report"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// These tests drive the model by handing it messages directly. They never drain
// tea.Cmd from a form, because huh re-arms the text input's cursor blink on every
// update and each blink tick sleeps for about half a second, so a naive drain
// makes the suite hang. Only this package's own commands are executed directly,
// and they never sleep.

// stubExec records the invocation it was given and returns canned output, so the
// model's form-to-invocation logic is testable with no CLI on PATH.
type stubExec struct {
	raw []byte
	err error
	got run.Invocation
}

func (s *stubExec) Run(inv run.Invocation, _ time.Duration) ([]byte, error) {
	s.got = inv
	return s.raw, s.err
}

func testEntries() []gallery.Entry {
	return []gallery.Entry{
		{ID: "dog_closeup", Filename: "dog_closeup.jpg", Description: "A white dog", Features: []string{"classification", "detection"}},
		{ID: "sign_board", Filename: "sign_board.png", Description: "A sign", Features: []string{"text"}},
	}
}

func testModel(t *testing.T, exec Executor) *Model {
	t.Helper()
	return New(Options{
		ProjectRoot: "/repo",
		Entries:     testEntries(),
		Exec:        exec,
		Binary:      "oci-vision",
		Timeout:     5 * time.Second,
	})
}

const analysisFixture = `{
  "image_path": "dog_closeup.jpg",
  "classification": {"model_version": "1.5.97", "labels": [
    {"name": "Dog", "confidence": 0.9925, "confidence_pct": 99.25}]},
  "detection": {"model_version": "1.3.557", "objects": [
    {"name": "Dog", "confidence": 0.982, "confidence_pct": 98.2,
     "bounding_polygon": {"normalized_vertices": [], "center": [0.39, 0.50]}}]},
  "text": null, "faces": null, "document": null,
  "available_features": ["classification", "detection"],
  "insights": ["Top label: Dog (99.2%)"]
}`

func TestNewStartsOnTheMenu(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 30})

	if model.screen != ScreenMenu {
		t.Fatalf("screen = %v, want the menu", model.screen)
	}
	if model.form == nil || model.form.State != huh.StateNormal {
		t.Fatal("the menu form must be built and normal up front")
	}
	if view := model.View().Content; !strings.Contains(view, "Analyze an image") {
		t.Fatalf("the menu should render its choices, got %q", view)
	}
}

// TestSeededImageIsRoutedToTheRightField is the guard for a silent clobber: a huh
// Select whose Value is not among its Options falls back to the first option on
// submit, so seeding a plain path into the picker made `-image missing.png` analyse
// dog_closeup.jpg instead of failing as it should.
func TestSeededImageIsRoutedToTheRightField(t *testing.T) {
	entries := testEntries()

	t.Run("gallery filename seeds the picker", func(t *testing.T) {
		answers := AnalyzeDefaults(AnalyzeSeed{Image: "sign_board.png"}, entries)
		if answers.Asset != "sign_board.png" {
			t.Errorf("Asset = %q, want the gallery filename", answers.Asset)
		}
		if answers.ImagePath != "" {
			t.Errorf("ImagePath = %q, want it left empty", answers.ImagePath)
		}
	})

	t.Run("gallery id resolves to its filename", func(t *testing.T) {
		answers := AnalyzeDefaults(AnalyzeSeed{Image: "dog_closeup"}, entries)
		if answers.Asset != "dog_closeup.jpg" {
			t.Errorf("Asset = %q, want the resolved filename", answers.Asset)
		}
	})

	t.Run("an external path does not go into the picker", func(t *testing.T) {
		answers := AnalyzeDefaults(AnalyzeSeed{Image: "/tmp/photo.png"}, entries)
		if answers.Asset != "" {
			t.Errorf("Asset = %q, want it empty so the picker cannot clobber the path", answers.Asset)
		}
		if answers.Image() != "/tmp/photo.png" {
			t.Errorf("Image() = %q, want the seeded path", answers.Image())
		}
	})

	t.Run("an explicit path wins over a gallery name", func(t *testing.T) {
		answers := AnalyzeDefaults(AnalyzeSeed{Image: "dog_closeup.jpg", ImagePath: "/tmp/photo.png"}, entries)
		if answers.Image() != "/tmp/photo.png" {
			t.Errorf("Image() = %q, want the explicit path", answers.Image())
		}
	})

	t.Run("no gallery leaves the path as the only route", func(t *testing.T) {
		answers := AnalyzeDefaults(AnalyzeSeed{Image: "photo.png"}, nil)
		if answers.Asset != "" || answers.Image() != "photo.png" {
			t.Errorf("Seed = %+v, want the path field", answers)
		}
	})

	t.Run("the seeded path reaches the invocation", func(t *testing.T) {
		exec := &stubExec{raw: []byte(analysisFixture)}
		model := New(Options{
			ProjectRoot: "/repo",
			Entries:     entries,
			Exec:        exec,
			Binary:      "oci-vision",
			Seed:        AnalyzeSeed{Image: "/tmp/photo.png"},
		})
		if cmd := model.analyzeCmd(); cmd == nil {
			t.Fatal("analyzeCmd should schedule work")
		} else {
			_ = cmd()
		}
		if got := exec.got.CommandLine(); !strings.Contains(got, "/tmp/photo.png") {
			t.Fatalf("argv = %q, want the seeded path", got)
		}
	})
}

// TestSeedOpensTheAnalyzeScreen keeps `--image` from dropping the user on the menu
// after they already said what to analyse.
func TestSeedOpensTheAnalyzeScreen(t *testing.T) {
	model := New(Options{
		ProjectRoot: "/repo",
		Entries:     testEntries(),
		Exec:        &stubExec{},
		Binary:      "oci-vision",
		Seed:        AnalyzeSeed{Image: "sign_board.png"},
	})
	if model.screen != ScreenAnalyze {
		t.Fatalf("screen = %v, want analyze", model.screen)
	}
	if model.analyze.Asset != "sign_board.png" {
		t.Fatalf("seed not applied: %+v", model.analyze)
	}
}

// TestKeyReleaseDoesNotAdvanceTheForm pins the bubbletea v2 press/release bug:
// handling both would fire every binding twice per keystroke.
func TestKeyReleaseDoesNotAdvanceTheForm(t *testing.T) {
	model := testModel(t, &stubExec{})

	_, _ = model.Update(tea.KeyReleaseMsg{Code: 'a'})
	if model.form == nil {
		t.Fatal("a key release must not clear or complete the form")
	}
	if model.stage != stageForm {
		t.Fatalf("a key release must not leave the form stage, got %v", model.stage)
	}

	_, _ = model.Update(tea.KeyPressMsg{Code: 'q', Text: "q"})
	if model.screen != ScreenMenu {
		t.Fatalf("typing must stay on the menu, got %v", model.screen)
	}
}

// TestEscLeavesAnOpenForm is the regression guard for a confirmed bug class.
//
// huh's default keymap binds Quit to ctrl+c ONLY (charm.land/huh/v2 keymap.go), and
// the sole path that sets StateAborted is key.Matches(msg, keymap.Quit). A huh form
// therefore NEVER aborts on esc. Delegating esc to the form left it installed: the
// user sat on a form that no key could leave, and the only remaining exit was
// ctrl+c, which quits the whole program instead of going back.
func TestEscLeavesAnOpenForm(t *testing.T) {
	// Every form screen, so the guard cannot be correct on one screen and absent on
	// another.
	cases := map[string]struct {
		action string
		screen Screen
	}{
		"analyze":  {ActionAnalyze, ScreenAnalyze},
		"compare":  {ActionCompare, ScreenCompare},
		"workflow": {ActionWorkflow, ScreenWorkflow},
		"config":   {ActionConfig, ScreenConfig},
	}

	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			model := testModel(t, &stubExec{})
			_ = model.Init()
			_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 30})

			// Open a real form by choosing the action from the menu.
			model.menu.Choice = c.action
			_ = model.finishMenu()
			if model.screen != c.screen || model.form == nil {
				t.Fatalf("setup: screen = %v, form installed = %v; want screen %v", model.screen, model.form != nil, c.screen)
			}

			_, _ = model.Update(tea.KeyPressMsg{Code: tea.KeyEscape})

			// esc must take the user back to the menu rather than doing nothing.
			if model.screen != ScreenMenu {
				t.Fatalf("esc left the user on screen %v: that form is a dead end, because huh never aborts on esc", model.screen)
			}
			// Escaping must leave a usable menu form behind, not a torn-down model.
			if model.form == nil || model.form.State != huh.StateNormal {
				t.Fatal("escaping the form must leave a normal menu form installed")
			}
			if !strings.Contains(model.notice, "Cancelled") {
				t.Errorf("notice = %q, want a cancellation notice", model.notice)
			}
			// The menu must be the live form: its choices have to render. A leftover form
			// from the abandoned screen would still swallow every later keystroke.
			if view := model.View().Content; !strings.Contains(view, "Analyze an image") {
				t.Fatalf("the menu form is not what renders after esc:\n%s", view)
			}

			// Nothing may still be swallowing keys: a later choice must take effect.
			model.menu.Choice = ActionCompare
			_ = model.finishMenu()
			if model.screen != ScreenCompare {
				t.Fatalf("a later menu choice did not take effect, screen = %v", model.screen)
			}
		})
	}
}

// TestEscBehaviourAroundTheFormShield pins the three behaviours the esc fix must
// not disturb: esc stays a no-op on the menu, a key RELEASE of esc never cancels
// (the same double-fire rule the rest of the key handling follows), and ctrl+c
// still quits from inside a form.
func TestEscBehaviourAroundTheFormShield(t *testing.T) {
	t.Run("esc on the menu does nothing", func(t *testing.T) {
		model := testModel(t, &stubExec{})
		_ = model.Init()
		if model.screen != ScreenMenu {
			t.Fatalf("setup: screen = %v, want the menu", model.screen)
		}

		_, cmd := model.Update(tea.KeyPressMsg{Code: tea.KeyEscape})
		if model.screen != ScreenMenu || model.stage != stageForm {
			t.Fatalf("esc on the menu changed state: screen = %v stage = %v", model.screen, model.stage)
		}
		if cmd != nil {
			if _, quits := cmd().(tea.QuitMsg); quits {
				t.Fatal("esc on the menu must not quit: ctrl+c is the advertised exit")
			}
		}
	})

	t.Run("an esc RELEASE does not cancel the form", func(t *testing.T) {
		model := testModel(t, &stubExec{})
		_ = model.Init()
		model.menu.Choice = ActionAnalyze
		_ = model.finishMenu()

		_, _ = model.Update(tea.KeyReleaseMsg{Code: tea.KeyEscape})
		if model.screen != ScreenAnalyze {
			t.Fatalf("an esc key RELEASE left screen %v; releases must not act", model.screen)
		}
	})

	t.Run("ctrl+c still quits from a form", func(t *testing.T) {
		model := testModel(t, &stubExec{})
		_ = model.Init()
		model.menu.Choice = ActionAnalyze
		_ = model.finishMenu()

		_, cmd := model.Update(tea.KeyPressMsg{Code: 'c', Text: "ctrl+c"})
		if cmd == nil {
			t.Fatal("ctrl+c must still quit")
		}
		if _, quits := cmd().(tea.QuitMsg); !quits {
			t.Fatalf("ctrl+c produced %T, want tea.QuitMsg", cmd())
		}
	})
}

// TestNarrowTerminalStillRenders is the "panic below 6 columns" regression: the
// pane width is clamped, so a split pane must not produce a negative repeat count.
func TestNarrowTerminalStillRenders(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()

	sizes := []tea.WindowSizeMsg{
		{Width: 200, Height: 60},
		{Width: 40, Height: 12},
		{Width: 24, Height: 10},
		{Width: 12, Height: 6},
		{Width: 5, Height: 3},
		{Width: 1, Height: 1},
		{Width: 0, Height: 0},
	}
	for _, size := range sizes {
		_, _ = model.Update(size)
		if view := model.View().Content; view == "" {
			t.Fatalf("a %dx%d window rendered nothing", size.Width, size.Height)
		}
	}

	// The same must hold with a result on screen, which renders many panes.
	_, _ = model.Update(outputMsg{kind: "analysis", raw: []byte(analysisFixture)})
	for _, size := range sizes {
		_, _ = model.Update(size)
		if view := model.View().Content; view == "" {
			t.Fatalf("a result at %dx%d rendered nothing", size.Width, size.Height)
		}
	}
}

// TestAnalysisRendersEveryReturnedFeature is the core value of the front-end: the
// decoded report must reach the screen with its numbers intact.
//
// The content assertions are on the rendered body, which is what the pager scrolls.
// The window is short enough that the report is taller than it, so asserting on the
// clipped view would only test the scrolling (covered separately).
func TestAnalysisRendersEveryReturnedFeature(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 40})

	_, _ = model.Update(outputMsg{kind: "analysis", raw: []byte(analysisFixture)})

	view := model.body
	for _, want := range []string{
		"dog_closeup.jpg", // the heading is the analysed image
		"Insights",        // the CLI's own insight lines
		"Top label: Dog (99.2%)",
		"Classification",
		"99.2%",
		"Object detection",
		"98.2%",
		"model 1.5.97",
	} {
		if !strings.Contains(view, want) {
			t.Fatalf("analysis view is missing %q:\n%s", want, view)
		}
	}
	// Only the features the CLI returned may be drawn: text, faces and document
	// were null in this payload.
	for _, unwanted := range []string{"Text / OCR", "Face detection", "Document AI"} {
		if strings.Contains(view, unwanted) {
			t.Fatalf("view drew %q for a feature the CLI did not return:\n%s", unwanted, view)
		}
	}
	// The rendered frame must still be on screen, not just in the model.
	if rendered := model.View().Content; !strings.Contains(rendered, "dog_closeup.jpg") {
		t.Fatalf("the rendered view lost the heading:\n%s", rendered)
	}
}

func TestComparisonRendersDeltas(t *testing.T) {
	const comparisonFixture = `{
      "left_image": "dog_closeup.jpg", "right_image": "sign_board.png",
      "shared_features": [], "left_only_features": ["detection"], "right_only_features": ["text"],
      "top_label_change": {"left": "Dog", "right": "-", "changed": true},
      "object_count_delta": -11,
      "object_deltas": [{"name": "Dog", "left": 5, "right": 0, "delta": -5}],
      "ocr_similarity": null, "ocr_line_delta": 2, "face_count_delta": 0,
      "document_field_delta": 0, "document_field_changes": [],
      "left_summary": {}, "right_summary": {}
    }`

	model := testModel(t, &stubExec{})
	_ = model.Init()
	_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 40})
	_, _ = model.Update(outputMsg{kind: "comparison", raw: []byte(comparisonFixture)})

	// The body is what the pager scrolls; the viewport clips it to the window.
	view := model.body
	for _, want := range []string{"dog_closeup.jpg vs sign_board.png", "Deltas", "-11", "Object changes", "-5", "text"} {
		if !strings.Contains(view, want) {
			t.Fatalf("comparison view is missing %q:\n%s", want, view)
		}
	}
}

// TestWorkflowRendersItsOwnShape covers the two workflow JSON shapes that render
// differently.
func TestWorkflowRendersItsOwnShape(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 40})

	_, _ = model.Update(outputMsg{kind: "receipt", raw: []byte(
		`{"field_count":2,"fields":{"Invoice Number":"INV-1001"},"table_count":1,"page_count":1}`)})
	view := model.body
	for _, want := range []string{"Receipt", "INV-1001", "Invoice Number", "pages"} {
		if !strings.Contains(view, want) {
			t.Fatalf("receipt view is missing %q:\n%s", want, view)
		}
	}

	_, _ = model.Update(outputMsg{kind: "archive-search", raw: []byte(
		`{"query":"INV-1001","match_count":1,"matches":[{"image":"invoice_demo.png","page_count":1,"field_count":2}]}`)})
	view = model.body
	for _, want := range []string{"Archive search", "INV-1001", "invoice_demo.png"} {
		if !strings.Contains(view, want) {
			t.Fatalf("archive-search view is missing %q:\n%s", want, view)
		}
	}
}

// TestFailureShowsTheCommandAndAProblemPanel keeps a broken CLI actionable instead
// of a blank screen.
func TestFailureShowsTheCommandAndAProblemPanel(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 40})

	_, _ = model.Update(outputMsg{
		kind:    "analysis",
		err:     errors.New("Error: Demo asset not found: missing.png"),
		command: "oci-vision analyze missing.png --demo --output-format json",
	})

	view := model.View().Content
	for _, want := range []string{"Problem", "Demo asset not found", "oci-vision analyze missing.png"} {
		if !strings.Contains(view, want) {
			t.Fatalf("failure view is missing %q:\n%s", want, view)
		}
	}
	if model.failure == nil {
		t.Fatal("the failure must be recorded so the hint can offer a retry")
	}
}

// TestResultKeysLeaveTheViewportAloneForScrolling is the key-conflict guard: q and r
// are handled before the viewport sees the message, so neither is swallowed.
func TestResultKeysLeaveTheViewportAloneForScrolling(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	model.screen = ScreenAnalyze
	_, _ = model.Update(outputMsg{kind: "analysis", raw: []byte(analysisFixture)})

	// Scrolling must not change the stage.
	_, _ = model.Update(tea.KeyPressMsg{Code: 'j', Text: "j"})
	if model.stage != stageResult {
		t.Fatalf("scrolling left the result stage, got %v", model.stage)
	}

	// r returns to the form that produced the result.
	_, _ = model.Update(tea.KeyPressMsg{Code: 'r', Text: "r"})
	if model.stage != stageForm {
		t.Fatalf("r should reopen the form, stage = %v", model.stage)
	}
	if model.screen != ScreenAnalyze {
		t.Fatalf("r should reopen the analyze form, screen = %v", model.screen)
	}

	// q returns to the menu.
	_, _ = model.Update(outputMsg{kind: "analysis", raw: []byte(analysisFixture)})
	_, _ = model.Update(tea.KeyPressMsg{Code: 'q', Text: "q"})
	if model.screen != ScreenMenu || model.stage != stageForm {
		t.Fatalf("q should return to the menu, screen = %v stage = %v", model.screen, model.stage)
	}
}

// TestResizeReflowsAnAlreadyLoadedResult pins that a resize after a result arrives
// re-renders rather than leaving stale widths on screen.
func TestResizeReflowsAnAlreadyLoadedResult(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	_, _ = model.Update(tea.WindowSizeMsg{Width: 120, Height: 40})
	_, _ = model.Update(outputMsg{kind: "analysis", raw: []byte(analysisFixture)})

	wide := model.body
	_, _ = model.Update(tea.WindowSizeMsg{Width: 44, Height: 20})
	narrow := model.body

	if wide == narrow {
		t.Fatal("the body did not change with the window width, so the reflow is not happening")
	}
	if !strings.Contains(narrow, "Classification") {
		t.Fatalf("the reflowed body lost its content:\n%s", narrow)
	}
}

func TestFinishMenuRoutesEveryAction(t *testing.T) {
	cases := map[string]Screen{
		ActionAnalyze:  ScreenAnalyze,
		ActionCompare:  ScreenCompare,
		ActionWorkflow: ScreenWorkflow,
		ActionConfig:   ScreenConfig,
	}
	for action, want := range cases {
		model := testModel(t, &stubExec{})
		model.menu.Choice = action
		cmd := model.finishMenu()
		if model.screen != want {
			t.Errorf("action %q: screen = %v, want %v", action, model.screen, want)
		}
		if cmd == nil {
			t.Errorf("action %q should schedule work", action)
		}
	}
}

// TestShowcaseAndGalleryRunFromTheMenu covers the two actions that are not forms.
func TestShowcaseAndGalleryRunFromTheMenu(t *testing.T) {
	exec := &stubExec{raw: []byte(`{"asset_count":4,"workflow_count":4,"comparison_count":2,
      "gallery":[],"batch":{},"comparisons":[],"workflows":{},"commands":{},"headlines":["hello"]}`)}

	model := testModel(t, exec)
	model.menu.Choice = ActionShowcase
	if cmd := model.finishMenu(); cmd == nil {
		t.Fatal("showcase should schedule work")
	}
	if model.stage != stageRunning {
		t.Fatalf("showcase should enter the running stage, got %v", model.stage)
	}

	model.menu.Choice = ActionGallery
	if cmd := model.finishMenu(); cmd == nil {
		t.Fatal("gallery should schedule work")
	}
}

// TestAnalyzeCommandSendsTheSelectedImageAndFeatures is the seam that cannot be
// driven through keystrokes: which invocation the form produces.
func TestAnalyzeCommandSendsTheSelectedImageAndFeatures(t *testing.T) {
	exec := &stubExec{raw: []byte(analysisFixture)}
	model := testModel(t, exec)
	model.screen = ScreenAnalyze
	model.analyze = AnalyzeAnswers{
		Asset:    "sign_board.png",
		Features: []string{"text"},
		Demo:     true,
	}

	if cmd := model.analyzeCmd(); cmd == nil {
		t.Fatal("analyzeCmd should schedule work")
	} else {
		_ = cmd() // our own command never sleeps
	}

	want := "oci-vision analyze sign_board.png --features text --demo --output-format json"
	if got := exec.got.CommandLine(); got != want {
		t.Fatalf("argv = %q, want %q", got, want)
	}
}

// TestTypedPathOverridesThePicker pins the documented field precedence.
func TestTypedPathOverridesThePicker(t *testing.T) {
	exec := &stubExec{raw: []byte(analysisFixture)}
	model := testModel(t, exec)
	model.screen = ScreenAnalyze
	model.analyze = AnalyzeAnswers{
		Asset:     "dog_closeup.jpg",
		ImagePath: "/tmp/custom.png",
		Features:  []string{"classification"},
		Demo:      true,
	}

	if cmd := model.analyzeCmd(); cmd == nil {
		t.Fatal("analyzeCmd should schedule work")
	} else {
		_ = cmd()
	}

	joined := exec.got.CommandLine()
	if !strings.Contains(joined, "/tmp/custom.png") {
		t.Fatalf("the typed path should win, got %q", joined)
	}
	if strings.Contains(joined, "dog_closeup.jpg") {
		t.Fatalf("the picker value should not also be sent, got %q", joined)
	}
}

// TestWorkflowCommandCarriesTheQuery covers the archive-search requirement reaching
// the invocation.
func TestWorkflowCommandCarriesTheQuery(t *testing.T) {
	exec := &stubExec{raw: []byte(`{"query":"INV-1001","match_count":0,"matches":[]}`)}
	model := testModel(t, exec)
	model.screen = ScreenWorkflow
	model.workflow = WorkflowAnswers{
		Kind:  "archive-search",
		Asset: "invoice_demo.png",
		Query: "INV-1001",
		Demo:  true,
	}

	if cmd := model.workflowCmd(); cmd == nil {
		t.Fatal("workflowCmd should schedule work")
	} else {
		_ = cmd()
	}

	want := "oci-vision workflow archive-search invoice_demo.png --query INV-1001 --demo"
	if got := exec.got.CommandLine(); got != want {
		t.Fatalf("argv = %q, want %q", got, want)
	}
}

// TestValidationFailureIsReportedWithoutRunningTheCli keeps a bad form from
// spawning a subprocess that would only fail.
func TestValidationFailureIsReportedWithoutRunningTheCli(t *testing.T) {
	exec := &stubExec{}
	model := testModel(t, exec)
	model.screen = ScreenAnalyze
	model.analyze = AnalyzeAnswers{Features: []string{"classification"}, Demo: true} // no image

	cmd := model.analyzeCmd()
	if cmd == nil {
		t.Fatal("a validation failure should still produce a message")
	}
	msg, ok := cmd().(outputMsg)
	if !ok {
		t.Fatalf("expected an outputMsg, got %T", cmd())
	}
	if msg.err == nil {
		t.Fatal("an image-less analysis must be refused")
	}
	if exec.got.Argv != nil {
		t.Fatalf("the CLI must not be run for an invalid form: %v", exec.got.Argv)
	}
}

// TestMissingExecutorIsReportedNotPanicked covers a mis-wired caller.
func TestMissingExecutorIsReportedNotPanicked(t *testing.T) {
	model := New(Options{Binary: "oci-vision", Entries: testEntries()})
	model.screen = ScreenAnalyze
	model.analyze = AnalyzeAnswers{Asset: "dog_image.png", Features: []string{"classification"}, Demo: true}

	msg, ok := model.execCmd(run.Analyze("oci-vision", "x.png", nil, "", true), "analysis", false)().(outputMsg)
	if !ok {
		t.Fatal("expected an outputMsg")
	}
	if msg.err == nil {
		t.Fatal("a nil executor must surface an error")
	}
}

func TestWorkflowKindOptionsCoverEveryKind(t *testing.T) {
	options := WorkflowOptions()
	if len(options) != len(run.WorkflowKinds) {
		t.Fatalf("options = %d, want %d", len(options), len(run.WorkflowKinds))
	}
}

// TestPagerKeysScrollLongReports is the guard for the render-the-body-instead-of-the-
// viewport bug: the body was drawn raw, so a report taller than the window was
// clipped at the bottom with no way to reach the rest of it.
func TestPagerKeysScrollLongReports(t *testing.T) {
	model := testModel(t, &stubExec{})
	_ = model.Init()
	// A short window guarantees the report is taller than the viewport.
	_, _ = model.Update(tea.WindowSizeMsg{Width: 100, Height: 20})
	_, _ = model.Update(outputMsg{kind: "analysis", raw: []byte(analysisFixture)})

	before := model.viewport.ScrollPercent()
	if before != 0 {
		t.Fatalf("a fresh result should start at the top, got %v", before)
	}

	for i := 0; i < 10; i++ {
		_, _ = model.Update(tea.KeyPressMsg{Code: tea.KeyDown, Text: "down"})
	}

	if after := model.viewport.ScrollPercent(); after <= before {
		t.Fatalf("the pager did not scroll: %v -> %v", before, after)
	}

	// The viewport must be what is drawn, otherwise the scrolled region is never
	// visible even though the offset moved.
	if view := model.View().Content; !strings.Contains(view, "Classification") {
		t.Fatalf("the scrolled view lost its content:\n%s", view)
	}
}

// TestNarrowViewDoesNotPanicAtTheMinimumWidth exercises the clamp directly, which
// is where a negative repeat count would come from.
func TestNarrowViewDoesNotPanicAtTheMinimumWidth(t *testing.T) {
	for width := -5; width <= minPaneWidth+2; width++ {
		rendered := Pane("title", "body", width)
		if rendered == "" {
			t.Fatalf("width %d rendered nothing", width)
		}
	}
}

// widestLine is the rendered column count of the widest line.
func widestLine(rendered string) int {
	widest := 0
	for _, line := range strings.Split(rendered, "\n") {
		if width := lipgloss.Width(line); width > widest {
			widest = width
		}
	}
	return widest
}

// TestPaneOccupiesExactlyItsWidth is the regression guard for the frame-width bug.
// lipgloss Width(w) sets the block's TOTAL width, frame included, so a pane must be
// handed the total it may occupy and must fill it exactly -- under-filling wastes
// the terminal and over-filling wraps every box.
func TestPaneOccupiesExactlyItsWidth(t *testing.T) {
	for _, width := range []int{26, 40, 60, 80, 100, 120, 200} {
		rendered := Pane("Classification", "a fairly long body line that would overflow if unmeasured", width)
		if got := widestLine(rendered); got != width {
			t.Errorf("Pane(width=%d) rendered %d columns, want exactly %d", width, got, width)
		}
	}
}

// TestPaneFillsItsInnerWidth pins the split between the frame and the text: the content
// area must be the total minus the frame, and a body line of exactly that length must
// not wrap.
func TestPaneFillsItsInnerWidth(t *testing.T) {
	for _, total := range []int{40, 60, 80, 100} {
		inner := innerWidth(total)
		if inner != total-paneChrome {
			t.Fatalf("innerWidth(%d) = %d, want %d", total, inner, total-paneChrome)
		}
		// A body of exactly the inner width must stay on ONE line, so the pane is
		// border + padding row + body + padding row + border = 5 lines.
		rendered := Pane("", strings.Repeat("x", inner), total)
		if lines := len(strings.Split(rendered, "\n")); lines != 5 {
			t.Errorf("inner-width body wrapped: %d lines for total=%d inner=%d\n%s", lines, total, inner, rendered)
		}
	}
}

// TestAnalysisReportFitsTheWidth applies the same guard to a real report, where
// several panes and several row layouts are involved.
func TestAnalysisReportFitsTheWidth(t *testing.T) {
	analysis, err := report.Decode[report.Analysis]([]byte(analysisFixture))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	for _, width := range []int{30, 44, 80, 100, 120, 200} {
		rendered := AnalysisReport(analysis, width)
		if got := widestLine(rendered); got > width {
			t.Errorf("AnalysisReport(width=%d) rendered %d columns:\n%s", width, got, rendered)
		}
	}
}

// TestClassificationRowsFitThePaneContentWidth is the row-level version of the same
// bug: a row wider than the pane's content area wraps, and a wrapped confidence bar
// is unreadable.
func TestClassificationRowsFitThePaneContentWidth(t *testing.T) {
	analysis, err := report.Decode[report.Analysis]([]byte(analysisFixture))
	if err != nil {
		t.Fatalf("Decode: %v", err)
	}
	for _, total := range []int{40, 60, 80, 100, 120} {
		inner := innerWidth(total)
		rows := ClassificationRows(analysis.Classification, inner)
		if got := widestLine(rows); got > inner {
			t.Errorf("classification rows at inner=%d rendered %d columns:\n%s", inner, got, rows)
		}
		// Each label stays on one line, plus the trailing "model ..." line, so the
		// non-empty line count must be exactly labels + 1.
		nonEmpty := 0
		for _, line := range strings.Split(rows, "\n") {
			if strings.TrimSpace(line) != "" {
				nonEmpty++
			}
		}
		if want := len(analysis.Classification.Labels) + 1; nonEmpty != want {
			t.Errorf("inner=%d produced %d non-empty lines for %d labels, want %d, so a row wrapped:\n%s",
				inner, nonEmpty, len(analysis.Classification.Labels), want, rows)
		}
	}
}
