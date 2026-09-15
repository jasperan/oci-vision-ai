// Package gallery reads the repository's own demo-gallery manifest.
//
// `oci-vision gallery` prints a Rich table, which is drawn for humans and has no
// machine-readable form, so the picker cannot get its options from the CLI. It
// reads src/oci_vision/gallery/manifest.json instead -- the exact file
// oci_vision.gallery.load_manifest() reads, so the two see the same assets.
//
// Nothing is invented: when the manifest cannot be found the caller falls back to
// a free-text image path field rather than offering a hard-coded list.
package gallery

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// ManifestRelPath is the gallery manifest, relative to the project root.
var ManifestRelPath = filepath.Join("src", "oci_vision", "gallery", "manifest.json")

// Entry is one curated demo asset.
type Entry struct {
	ID          string   `json:"id"`
	Filename    string   `json:"filename"`
	Description string   `json:"description"`
	Features    []string `json:"features"`
}

// Manifest is the gallery manifest document.
type Manifest struct {
	Images []Entry `json:"images"`
}

// Label renders an entry for a picker row: the filename, plus what it is good for.
func (e Entry) Label() string {
	if e.Description == "" {
		return e.Filename
	}
	return e.Filename + "  -  " + e.Description
}

// Load reads the gallery manifest under projectRoot.
func Load(projectRoot string) ([]Entry, error) {
	path := filepath.Join(projectRoot, ManifestRelPath)
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read gallery manifest: %w", err)
	}
	var manifest Manifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return nil, fmt.Errorf("decode gallery manifest: %w", err)
	}
	return manifest.Images, nil
}

// FindProjectRoot walks up from the working directory, then from the executable,
// looking for the checkout that owns the gallery manifest.
//
// The binary may be built anywhere (`go run ./gotui/cmd/oci-vision-tui` puts it
// in a temp dir), so both anchors are tried. An empty string means "not found",
// which callers must treat as "no picker", never as an error the user has to fix.
func FindProjectRoot() string {
	if wd, err := os.Getwd(); err == nil {
		if root := walkUp(wd); root != "" {
			return root
		}
	}
	if executable, err := os.Executable(); err == nil {
		if root := walkUp(filepath.Dir(executable)); root != "" {
			return root
		}
	}
	return ""
}

// walkUp checks dir and its ancestors for the manifest, up to a fixed depth so a
// missing manifest cannot walk to the filesystem root.
func walkUp(dir string) string {
	for i := 0; i < 6 && dir != ""; i++ {
		if _, err := os.Stat(filepath.Join(dir, ManifestRelPath)); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return ""
}
