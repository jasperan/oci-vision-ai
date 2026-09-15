package tui

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"regexp"
	"strings"
	"time"

	"github.com/jasperan/oci-vision-ai/gotui/internal/run"
)

// DefaultTimeout bounds every subprocess.
//
// A live OCI Vision call is slow but has to end; without a bound an unreachable
// service would hang the TUI forever, which is the failure mode this front-end
// exists to avoid. Demo mode returns in milliseconds, so the bound is generous.
const DefaultTimeout = 5 * time.Minute

// Executor runs a prepared invocation. It is an interface so the model's
// form-to-invocation logic can be tested without a CLI on PATH or an OCI account,
// which is the only way it can be tested here.
type Executor interface {
	Run(inv run.Invocation, timeout time.Duration) ([]byte, error)
}

// ShellExec runs the real oci-vision CLI.
type ShellExec struct {
	// Dir is the working directory for the child; empty means inherit.
	//
	// It matters: demo mode resolves a bare gallery filename against the repo's
	// bundled assets, so the child must start in the checkout.
	Dir string
}

// Run executes the invocation and returns stdout.
//
// stdout and stderr are captured separately because the JSON document is the
// whole of stdout on success, while anything Rich printed -- an error panel, a
// warning -- lands on stderr. Merging them would corrupt the JSON.
func (e ShellExec) Run(inv run.Invocation, timeout time.Duration) ([]byte, error) {
	if len(inv.Argv) == 0 {
		return nil, errors.New("empty invocation")
	}

	ctx := context.Background()
	var cancel context.CancelFunc
	if timeout > 0 {
		ctx, cancel = context.WithTimeout(ctx, timeout)
		defer cancel()
	}

	cmd := exec.CommandContext(ctx, inv.Argv[0], inv.Argv[1:]...)
	cmd.Dir = e.Dir
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()

	if ctx.Err() == context.DeadlineExceeded {
		return stdout.Bytes(), fmt.Errorf("timed out after %s", timeout)
	}
	if err != nil {
		if _, lookErr := exec.LookPath(inv.Argv[0]); lookErr != nil {
			return nil, fmt.Errorf("%s not found on PATH: %w", inv.Argv[0], lookErr)
		}
		// The CLI's own message is far more useful than "exit status 1".
		if message := bestErrorLine(stderr.String(), stdout.String()); message != "" {
			return stdout.Bytes(), errors.New(message)
		}
		return stdout.Bytes(), err
	}
	return stdout.Bytes(), nil
}

// errorLine matches the CLI's Rich-rendered failure, e.g.
//
//	Error: Demo asset not found: missing.png. Known demo assets: ...
//
// and its exception form ("FileNotFoundError: ...").
var errorLine = regexp.MustCompile(`^(Error:|[A-Za-z_][A-Za-z0-9_.]*(Error|Exception)\s*:)`)

// bestErrorLine picks the most useful line out of captured output.
//
// Order: the CLI's own "Error:" line first, then a real exception header, then
// the first line that is actually words. Panels are box-drawn, so border
// characters are stripped before a line is considered.
func bestErrorLine(streams ...string) string {
	fallback := ""
	for _, stream := range streams {
		for _, line := range strings.Split(stream, "\n") {
			text := strings.TrimSpace(stripANSI(line))
			text = strings.Trim(text, "│┃─╭╮╰╯ ")
			text = strings.TrimSpace(text)
			if text == "" || !hasWordRune(text) {
				continue
			}
			if errorLine.MatchString(text) {
				return text
			}
			if fallback == "" {
				fallback = text
			}
		}
	}
	return fallback
}

func hasWordRune(s string) bool {
	return strings.IndexFunc(s, func(r rune) bool {
		return (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9')
	}) >= 0
}

// stripANSI removes SGR sequences so a Rich-coloured message can be matched.
func stripANSI(s string) string {
	var b strings.Builder
	escaping := false
	for _, r := range s {
		switch {
		case escaping:
			if r == 'm' {
				escaping = false
			}
		case r == 0x1b:
			escaping = true
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// ExtractJSON returns the JSON document inside captured stdout.
//
// The CLI prints one document, but a future warning line printed ahead of it would
// otherwise break the decode, so the document is located by its own delimiters: the
// earliest '[' or '{' starts it, and the last matching closer ends it. Choosing the
// opener by position, not by trying objects first, is what keeps a top-level array
// from being silently unwrapped into its first element.
func ExtractJSON(stdout []byte) ([]byte, error) {
	text := stripANSI(string(stdout))

	objectStart := strings.Index(text, "{")
	arrayStart := strings.Index(text, "[")

	start, closer := objectStart, "}"
	if arrayStart >= 0 && (objectStart < 0 || arrayStart < objectStart) {
		start, closer = arrayStart, "]"
	}
	if start < 0 {
		return nil, fmt.Errorf("the CLI returned no JSON document: %s", firstLine(text))
	}

	end := strings.LastIndex(text, closer)
	if end < start {
		return nil, fmt.Errorf("the CLI returned no JSON document: %s", firstLine(text))
	}
	return []byte(text[start : end+1]), nil
}

// firstLine returns the first non-empty line, for an error message.
func firstLine(text string) string {
	for _, line := range strings.Split(text, "\n") {
		if trimmed := strings.TrimSpace(line); trimmed != "" {
			return Truncate(trimmed, 160)
		}
	}
	return "(no output)"
}
