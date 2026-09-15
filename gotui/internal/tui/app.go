// Package tui is the Go front-end's terminal UI, built on charm.land/bubbletea/v2
// and charm.land/huh/v2.
//
// It never analyses an image. Every result on screen was produced by the
// oci-vision CLI, which this front-end runs and renders, so a Go user and a
// Python user get identical numbers.
package tui

import (
	"errors"
	"strings"
	"time"

	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/huh/v2"

	"github.com/jasperan/oci-vision-ai/gotui/internal/gallery"
	"github.com/jasperan/oci-vision-ai/gotui/internal/report"
	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// Screen identifies the active form.
type Screen int

// Screens.
const (
	ScreenMenu Screen = iota
	ScreenAnalyze
	ScreenCompare
	ScreenWorkflow
	ScreenConfig
)

// stage separates the three kinds of frame the UI shows.
//
// A result is NOT a screen: it is a stage the user can only scroll, run again, or
// leave. Keeping a continue form out of the result frame is what avoids a key
// conflict between the viewport's scrolling keys and a form's own arrow handling.
type stage int

const (
	stageForm stage = iota
	stageRunning
	stageResult
)

// Options configure a TUI run.
type Options struct {
	ProjectRoot string
	Entries     []gallery.Entry
	Exec        Executor
	Binary      string
	Timeout     time.Duration
	Seed        AnalyzeSeed
}

// outputMsg carries a finished subprocess back into the update loop.
//
// The raw bytes travel, not a rendered string: rendering happens where the
// current width is known, so a resize reflows an already-loaded result instead of
// leaving it at the old width.
type outputMsg struct {
	// kind is the workflow kind, or "analysis"/"comparison"/"showcase"/"text".
	kind string
	// raw is the subprocess stdout.
	raw []byte
	// passthrough marks output that renders itself, so only colour codes are
	// stripped and the CLI's own layout is preserved.
	passthrough bool
	err         error
	command     string
}

// Model is the root bubbletea model.
type Model struct {
	width  int
	height int
	opts   Options

	stage  stage
	screen Screen
	form   *huh.Form

	menu     MenuAnswers
	analyze  AnalyzeAnswers
	compare  CompareAnswers
	workflow WorkflowAnswers
	configA  ConfigAnswers

	viewport viewport.Model

	title   string
	body    string
	command string
	failure error
	notice  string

	// last is the most recent finished output, kept so a resize can re-render it.
	last *outputMsg
}

// New builds the root model and shows the menu.
func New(opts Options) *Model {
	if opts.Timeout <= 0 {
		opts.Timeout = DefaultTimeout
	}
	m := Model{
		width:    100,
		height:   30,
		opts:     opts,
		stage:    stageForm,
		screen:   ScreenMenu,
		analyze:  AnalyzeDefaults(opts.Seed, opts.Entries),
		viewport: viewport.New(viewport.WithWidth(96), viewport.WithHeight(20)),
	}
	// A flag that named an image means the user wants to analyse it, so the form
	// that uses the seed opens immediately instead of the menu.
	if strings.TrimSpace(opts.Seed.Image) != "" || strings.TrimSpace(opts.Seed.ImagePath) != "" {
		m.screen = ScreenAnalyze
	}
	m.form = m.buildForm()
	m.resize()
	return &m
}

// buildForm builds the form for the active screen.
//
// Every screen transition goes through here, so no form can be left at huh's
// default zero width (which renders as blank lines).
func (m *Model) buildForm() *huh.Form {
	switch m.screen {
	case ScreenAnalyze:
		return AnalyzeForm(&m.analyze, m.opts.Entries)
	case ScreenCompare:
		return CompareForm(&m.compare, m.opts.Entries)
	case ScreenWorkflow:
		return WorkflowForm(&m.workflow, m.opts.Entries)
	case ScreenConfig:
		return ConfigForm(&m.configA)
	default:
		return MenuForm(&m.menu.Choice, m.opts.ProjectRoot)
	}
}

// setForm installs a freshly built form, sizes it, and returns its first command.
func (m *Model) setForm(form *huh.Form) tea.Cmd {
	m.form = form
	m.resize()
	return m.form.Init()
}

// resize applies the current window size to the form and the viewport.
//
// huh.NewForm leaves the form at width 0 until something sets it, and a
// zero-width field renders as blank lines. Both dimensions are clamped, so a
// terminal narrower or shorter than the minimum cannot produce a negative size.
func (m *Model) resize() {
	if m.form != nil {
		width := max(m.width-4, minPaneWidth)
		height := max(m.height-2, 5)
		m.form = m.form.WithWidth(width).WithHeight(height)
	}
	m.viewport.SetWidth(max(m.width-2, minPaneWidth))
	m.viewport.SetHeight(max(m.height-4, 3))
}

// Init implements tea.Model.
func (m *Model) Init() tea.Cmd { return m.form.Init() }

// --- commands ----------------------------------------------------------------------

// analyzeCmd runs `oci-vision analyze --output-format json`.
func (m *Model) analyzeCmd() tea.Cmd {
	if err := ValidateImageRequired(m.analyze); err != nil {
		return failureCmd(err)
	}
	if err := run.ValidateFeatureNames(m.analyze.Features); err != nil {
		return failureCmd(err)
	}
	inv := run.Analyze(m.opts.Binary, m.analyze.Image(), m.analyze.Features,
		strings.TrimSpace(m.analyze.ModelID), m.analyze.Demo)
	return m.execCmd(inv, "analysis", false)
}

// compareCmd runs `oci-vision compare --output-format json`.
func (m *Model) compareCmd() tea.Cmd {
	if err := ValidateComparePairs(m.compare); err != nil {
		return failureCmd(err)
	}
	if err := run.ValidateFeatureNames(m.compare.Features); err != nil {
		return failureCmd(err)
	}
	inv := run.Compare(m.opts.Binary, m.compare.LeftImage(), m.compare.RightImage(),
		m.compare.Features, m.compare.Demo)
	return m.execCmd(inv, "comparison", false)
}

// workflowCmd runs `oci-vision workflow KIND IMAGE`.
func (m *Model) workflowCmd() tea.Cmd {
	if err := ValidateWorkflow(m.workflow); err != nil {
		return failureCmd(err)
	}
	inv, err := run.Workflow(m.opts.Binary, m.workflow.Kind, m.workflow.Image(),
		m.workflow.Query, m.workflow.Demo)
	if err != nil {
		return failureCmd(err)
	}
	return m.execCmd(inv, m.workflow.Kind, false)
}

// showcaseCmd runs `oci-vision showcase --output-format json`.
func (m *Model) showcaseCmd() tea.Cmd {
	return m.execCmd(run.Showcase(m.opts.Binary, true), "showcase", false)
}

// galleryCmd runs `oci-vision gallery`, which prints a Rich table.
func (m *Model) galleryCmd() tea.Cmd {
	return m.execCmd(run.Gallery(m.opts.Binary), "gallery", true)
}

// configCmd runs `oci-vision config`.
func (m *Model) configCmd() tea.Cmd {
	inv := run.Config(m.opts.Binary, m.configA.Demo, strings.TrimSpace(m.configA.Profile))
	return m.execCmd(inv, "config", true)
}

// failureCmd turns a validation failure into an output message, so a bad
// combination is reported in the same panel as a failed subprocess.
func failureCmd(err error) tea.Cmd {
	return func() tea.Msg { return outputMsg{err: err} }
}

// execCmd builds the command that runs one invocation.
//
// The subprocess is bounded by the configured timeout and a failure is returned
// in the message rather than raised, so a broken CLI shows as an error panel
// instead of taking the UI down.
func (m *Model) execCmd(inv run.Invocation, kind string, passthrough bool) tea.Cmd {
	exec := m.opts.Exec
	timeout := m.opts.Timeout
	return func() tea.Msg {
		if exec == nil {
			return outputMsg{kind: kind, err: errNoExecutor, command: inv.CommandLine()}
		}
		raw, err := exec.Run(inv, timeout)
		return outputMsg{
			kind:        kind,
			raw:         raw,
			passthrough: passthrough,
			err:         err,
			command:     inv.CommandLine(),
		}
	}
}

// --- update ------------------------------------------------------------------------

// Update implements tea.Model.
func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.resize()
		// Re-render whatever is on screen at the new width.
		if m.last != nil && m.stage == stageResult {
			m.render(*m.last)
		} else if m.stage == stageRunning {
			m.viewport.SetContent(m.body)
		}
		return m, nil

	case outputMsg:
		m.stage = stageResult
		m.form = nil
		m.last = &msg
		m.render(msg)
		return m, nil

	case tea.KeyPressMsg:
		// Only key PRESSES are handled. bubbletea v2 also delivers key
		// releases, and acting on both would fire every binding twice per
		// keystroke.
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}
		if m.stage == stageResult {
			return m.updateResult(msg)
		}
		// esc abandons the open form and returns to the menu.
		//
		// It has to be handled here rather than delegated to the form. huh's
		// default keymap binds Quit to ctrl+c ONLY, and the sole path that sets
		// StateAborted is key.Matches(msg, keymap.Quit), so a form never aborts on
		// esc. Delegating it left the form installed with no way back to the menu,
		// and the only remaining exit was ctrl+c -- which quits the whole program
		// instead of going back.
		//
		// On the menu itself there is nothing to go back to, so esc stays a no-op
		// and is not advertised there.
		if msg.String() == "esc" && m.stage == stageForm && m.screen != ScreenMenu {
			return m, m.cancelForm()
		}
		m.notice = ""
	}

	if m.stage != stageForm || m.form == nil {
		return m, nil
	}

	updated, cmd := m.form.Update(msg)
	if form, ok := updated.(*huh.Form); ok {
		m.form = form
	}
	if m.form.State == huh.StateAborted {
		// Unreachable from a keystroke: esc is intercepted above, and ctrl+c is
		// handled before the form ever sees the message. Kept so a future keymap
		// change cannot make an abort fall through to the submit path.
		return m, tea.Quit
	}
	if m.form.State != huh.StateCompleted {
		return m, cmd
	}
	return m, m.advance()
}

// updateResult handles keys on the result stage.
//
// q and r are read before the viewport sees the message, so neither can be
// swallowed by the viewport's own bindings.
func (m *Model) updateResult(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "q", "esc":
		return m, m.toMenu()
	case "r":
		return m, m.runAgain()
	}
	var cmd tea.Cmd
	m.viewport, cmd = m.viewport.Update(msg)
	return m, cmd
}

// render turns a raw subprocess result into the title and body on screen.
func (m *Model) render(msg outputMsg) {
	m.command = msg.command
	m.failure = msg.err
	m.title, m.body = m.describe(msg)
	m.viewport.SetContent(m.body)
	m.viewport.GotoTop()
}

// contentWidth is the columns a result pane may occupy: the terminal minus the
// viewport's own two columns of breathing room.
//
// The viewport is sized to the same figure, so a pane drawn at this width fits
// exactly and its frame cannot wrap.
func (m *Model) contentWidth() int { return max(m.width-2, minPaneWidth) }

// describe builds the title and the FINISHED body for one output message.
//
// The body is fully framed here, which is why View only prints it: a report is
// already a stack of panes, so wrapping it again would make every inner frame
// wider than its container and wrap it.
func (m *Model) describe(msg outputMsg) (string, string) {
	width := m.contentWidth()

	if msg.err != nil {
		// A failure panel is: the command that failed, then the cause. The command
		// is the fastest way to reproduce the problem by hand, so it comes first.
		var body strings.Builder
		if msg.command != "" {
			body.WriteString("$ " + msg.command + "\n\n")
		}

		// The extracted message is a single line, while the CLI's own output carries
		// the full text (Rich wraps it). Prefer the fuller of the two when they
		// describe the same failure, but never show both: that doubles the panel for
		// no gain. If the output says something else entirely, the extracted message
		// is the only trustworthy summary.
		raw := strings.TrimSpace(stripANSI(string(msg.raw)))
		if strings.Contains(raw, msg.err.Error()) && len(raw) > len(msg.err.Error()) {
			body.WriteString(raw)
		} else {
			body.WriteString(msg.err.Error())
		}
		return "Problem", Pane("Problem", body.String(), width)
	}

	if msg.passthrough {
		// gallery and config render themselves; only the colour codes are
		// stripped, so the CLI's own layout is preserved.
		title := friendlyTitle(msg.kind)
		return title, Pane(title, stripANSI(string(msg.raw)), width)
	}

	data, err := ExtractJSON(msg.raw)
	if err != nil {
		return "Problem", Pane("Problem", err.Error(), width)
	}

	switch msg.kind {
	case "analysis":
		analysis, err := report.Decode[report.Analysis](data)
		if err != nil {
			return "Problem", Pane("Problem", err.Error(), width)
		}
		title := analysis.ImagePath
		return title, Heading(title, width) + "\n\n" + AnalysisReport(analysis, width)

	case "comparison":
		comparison, err := report.Decode[report.Comparison](data)
		if err != nil {
			return "Problem", Pane("Problem", err.Error(), width)
		}
		title := comparison.LeftImage + " vs " + comparison.RightImage
		return title, Heading(title, width) + "\n\n" + ComparisonReport(comparison, width)

	case "showcase":
		showcase, err := report.Decode[report.Showcase](data)
		if err != nil {
			return "Problem", Pane("Problem", err.Error(), width)
		}
		title := "Showcase snapshot"
		return title, Heading(title, width) + "\n\n" + ShowcaseReport(showcase, width)

	default:
		title := friendlyTitle(msg.kind)
		return title, Heading(title, width) + "\n\n" + WorkflowReport(msg.kind, data, width)
	}
}

// friendlyTitle renders a human title for a result kind.
func friendlyTitle(kind string) string {
	switch kind {
	case "gallery":
		return "Demo gallery"
	case "config":
		return "Configuration"
	case "showcase":
		return "Showcase snapshot"
	case "":
		return "Result"
	default:
		return strings.ToUpper(kind[:1]) + kind[1:]
	}
}

// showRunning puts the in-flight state on screen.
func (m *Model) showRunning(title, message string) {
	m.stage = stageRunning
	m.title = title
	m.body = Pane(title, message, m.contentWidth())
	m.command = ""
	m.failure = nil
	m.viewport.SetContent(m.body)
	m.viewport.GotoTop()
}

// cancelForm abandons the open form and returns to the menu.
//
// This is the only way back out of a form other than submitting it: huh binds its
// Quit key to ctrl+c alone, so a form cannot abort itself on esc (see Update).
func (m *Model) cancelForm() tea.Cmd {
	cmd := m.toMenu()
	m.notice = "Cancelled."
	return cmd
}

// advance reacts to a finished form.
func (m *Model) advance() tea.Cmd {
	state := m.form.State
	m.form = nil
	m.failure = nil

	if state == huh.StateAborted {
		// Unreachable by keystroke, for the same reason as the check in Update.
		return tea.Quit
	}

	switch m.screen {
	case ScreenAnalyze:
		if err := ValidateImageRequired(m.analyze); err != nil {
			return failureCmd(err)
		}
		m.showRunning("Analyzing "+m.analyze.Image(), "Running oci-vision analyze...")
		return m.analyzeCmd()

	case ScreenCompare:
		if err := ValidateComparePairs(m.compare); err != nil {
			return failureCmd(err)
		}
		m.showRunning("Comparing", "Running oci-vision compare...")
		return m.compareCmd()

	case ScreenWorkflow:
		if err := ValidateWorkflow(m.workflow); err != nil {
			return failureCmd(err)
		}
		m.showRunning("Workflow: "+m.workflow.Kind, "Running the workflow...")
		return m.workflowCmd()

	case ScreenConfig:
		m.showRunning("Configuration", "Checking configuration...")
		return m.configCmd()

	default:
		return m.finishMenu()
	}
}

// finishMenu routes the top-level menu selection.
func (m *Model) finishMenu() tea.Cmd {
	switch m.menu.Choice {
	case ActionAnalyze:
		return m.openScreen(ScreenAnalyze)

	case ActionCompare:
		return m.openScreen(ScreenCompare)

	case ActionWorkflow:
		return m.openScreen(ScreenWorkflow)

	case ActionShowcase:
		m.showRunning("Showcase snapshot", "Running oci-vision showcase...")
		return m.showcaseCmd()

	case ActionGallery:
		m.showRunning("Demo gallery", "Running oci-vision gallery...")
		return m.galleryCmd()

	case ActionConfig:
		return m.openScreen(ScreenConfig)

	default:
		return tea.Quit
	}
}

// openScreen shows a form screen.
func (m *Model) openScreen(screen Screen) tea.Cmd {
	m.screen = screen
	m.stage = stageForm
	m.menu.Choice = ""
	m.last = nil
	m.failure = nil
	return m.setForm(m.buildForm())
}

// toMenu returns to the menu from a result.
func (m *Model) toMenu() tea.Cmd { return m.openScreen(ScreenMenu) }

// runAgain reopens the form that produced the current result.
//
// Showcase and gallery are run straight from the menu rather than from a form, so
// for those the menu is the only sensible destination.
func (m *Model) runAgain() tea.Cmd {
	if m.screen == ScreenMenu {
		return m.openScreen(ScreenMenu)
	}
	m.stage = stageForm
	m.last = nil
	m.failure = nil
	return m.setForm(m.buildForm())
}

// --- view --------------------------------------------------------------------------

// View implements tea.Model.
func (m *Model) View() tea.View {
	var body strings.Builder

	body.WriteString(Header(m.demoMode(), m.width))
	body.WriteString("\n\n")

	if m.stage == stageForm {
		if m.form != nil {
			body.WriteString(m.form.View())
			body.WriteString("\n\n")
		}
		body.WriteString(Footer(m.hint(), m.width))

		view := tea.NewView(body.String())
		view.AltScreen = true
		return view
	}

	if m.title != "" {
		// The viewport is what actually draws the body, so the pager keys have a
		// visible effect and a report longer than the window stays readable. The
		// body it holds is already framed, so it is not wrapped again.
		body.WriteString(m.viewport.View() + "\n\n")
	}
	body.WriteString(Footer(m.resultHint(), m.width))

	view := tea.NewView(body.String())
	view.AltScreen = true
	return view
}

// demoMode reports whether the active flow will run offline.
//
// The header states the mode because it decides whether OCI credentials are
// needed, which is the first thing a user wants to know from a screenshot.
func (m *Model) demoMode() bool {
	switch m.screen {
	case ScreenCompare:
		return m.compare.Demo
	case ScreenWorkflow:
		return m.workflow.Demo
	case ScreenConfig:
		return m.configA.Demo
	default:
		return m.analyze.Demo
	}
}

// hint is the key-hint bar for form screens.
//
// esc is advertised only where it does something: it returns to the menu from a
// form screen, and is a no-op on the menu itself.
func (m *Model) hint() string {
	switch m.screen {
	case ScreenAnalyze, ScreenCompare, ScreenWorkflow, ScreenConfig:
		return "tab next - shift+tab back - enter submit - esc back - ctrl+c quit"
	default:
		return "arrows move - enter selects - ctrl+c quits"
	}
}

// resultHint is the key-hint bar for the result stage.
func (m *Model) resultHint() string {
	const scroll = "up/down scroll - pgup/pgdn page - g/G top or bottom"
	if m.failure != nil {
		return "r opens the form again - q back to the menu - " + scroll
	}
	return scroll + " - r run again - q back to the menu"
}

// errNoExecutor guards a Model built without a runner, which only a mis-wired
// caller can produce.
var errNoExecutor = errors.New("no executor configured")

// AccessibleNotice explains the mode switch a screen-reader user gets.
//
// The full-screen UI cannot serve a screen reader: an embedded huh form ignores
// WithAccessible (only Form.Run consults it), so this front-end routes to the
// plain path instead of pretending otherwise.
const AccessibleNotice = "ACCESSIBLE is set: using plain output instead of the full-screen UI."
