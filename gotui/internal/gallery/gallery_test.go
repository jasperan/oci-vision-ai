package gallery

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// writeManifest creates a minimal checkout containing the gallery manifest at the
// path Load expects.
func writeManifest(t *testing.T, body string) string {
	t.Helper()
	root := t.TempDir()
	path := filepath.Join(root, ManifestRelPath)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatalf("write manifest: %v", err)
	}
	return root
}

const manifestBody = `{
  "images": [
    {"id": "dog_closeup", "filename": "dog_closeup.jpg", "description": "A white dog", "features": ["classification", "detection"]},
    {"id": "sign_board", "filename": "sign_board.png", "description": "", "features": ["text"]}
  ]
}`

func TestLoadReadsTheReposOwnManifest(t *testing.T) {
	root := writeManifest(t, manifestBody)

	entries, err := Load(root)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if len(entries) != 2 {
		t.Fatalf("entries = %d, want 2", len(entries))
	}
	if entries[0].Filename != "dog_closeup.jpg" {
		t.Errorf("first entry = %+v", entries[0])
	}
	if entries[0].Features[0] != "classification" {
		t.Errorf("features = %v", entries[0].Features)
	}
}

// TestLabelAlwaysNamesTheFile is what makes the picker usable: the value sent to
// the CLI is the filename, and the row must show that same name.
func TestLabelAlwaysNamesTheFile(t *testing.T) {
	withDescription := Entry{Filename: "dog_closeup.jpg", Description: "A white dog"}
	if got := withDescription.Label(); got == "dog_closeup.jpg" {
		t.Errorf("Label() = %q, the description should be included", got)
	}
	if !strings.Contains(withDescription.Label(), "dog_closeup.jpg") {
		t.Errorf("Label() = %q, must contain the filename the CLI receives", withDescription.Label())
	}

	withoutDescription := Entry{Filename: "sign_board.png"}
	if got := withoutDescription.Label(); got != "sign_board.png" {
		t.Errorf("Label() = %q, want just the filename", got)
	}
}

func TestLoadReportsAMissingManifest(t *testing.T) {
	if _, err := Load(t.TempDir()); err == nil {
		t.Fatal("a missing manifest must be reported so the caller can fall back")
	}
}

func TestLoadReportsMalformedJSON(t *testing.T) {
	root := writeManifest(t, `{"images": [`)
	if _, err := Load(root); err == nil {
		t.Fatal("malformed JSON must be reported")
	}
}

// TestFindProjectRootWalksUpFromAWorkingDirectory pins the search that lets a
// binary built anywhere still find the checkout.
func TestFindProjectRootWalksUpFromAWorkingDirectory(t *testing.T) {
	root := writeManifest(t, manifestBody)
	nested := filepath.Join(root, "gotui", "cmd", "oci-vision-tui")
	if err := os.MkdirAll(nested, 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}

	previous, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	if err := os.Chdir(nested); err != nil {
		t.Fatalf("chdir: %v", err)
	}
	t.Cleanup(func() { _ = os.Chdir(previous) })

	if got := FindProjectRoot(); got == "" {
		t.Fatal("FindProjectRoot found nothing from a nested directory")
	}
}

// TestWalkUpReturnsEmptyOutsideACheckout documents the fallback contract: an empty
// string means "no picker", never an error the user has to fix.
func TestWalkUpReturnsEmptyOutsideACheckout(t *testing.T) {
	if got := walkUp(t.TempDir()); got != "" {
		t.Fatalf("walkUp = %q, want empty outside a checkout", got)
	}
}
