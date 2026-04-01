"use client";

import { useState, useCallback, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

interface SurfaceCard {
  id: string;
  icon: string;
  title: string;
  snippet: string;
  brief: string;
  detail: string;
}

const SURFACES: SurfaceCard[] = [
  {
    id: "cli",
    icon: "\u2328\uFE0F",
    title: "CLI",
    snippet: "oci-vision analyze img.jpg --demo",
    brief: "Rich tables, JSON/HTML export",
    detail:
      "Full-featured command-line interface built with Typer. Supports all 6 vision features, multiple output formats (table, JSON, HTML), and piping results to other tools. Use --demo for offline analysis with gallery fixtures.",
  },
  {
    id: "tui",
    icon: "\uD83D\uDCCA",
    title: "TUI / Cockpit",
    snippet: "oci-vision cockpit --demo",
    brief: "Textual framework, gallery browsing",
    detail:
      "Terminal dashboard built with the Textual framework. Browse the demo gallery, run analyses interactively, and view results in a split-pane layout with real-time confidence bars and overlay previews.",
  },
  {
    id: "web",
    icon: "\uD83C\uDF10",
    title: "Web Dashboard",
    snippet: "oci-vision web --demo",
    brief: "FastAPI, drag-and-drop, overlays",
    detail:
      "FastAPI-powered web interface at localhost:8000. Drag-and-drop image upload, bounding box overlays rendered in-browser, tabbed results for each feature, and exportable analysis reports.",
  },
  {
    id: "notebooks",
    icon: "\uD83D\uDCD3",
    title: "Notebooks",
    snippet: "jupyter notebook notebooks/",
    brief: "7 guided walkthroughs",
    detail:
      "Seven Jupyter notebooks from 01_quickstart through 07_custom_models. Each notebook runs in demo mode by default, with inline visualizations, step-by-step explanations, and exercises for hands-on learning.",
  },
];

/* ------------------------------------------------------------------ */
/*  Syntax-highlighted code block helper                               */
/* ------------------------------------------------------------------ */

interface Token {
  text: string;
  color: string;
}

function tokenizePython(line: string): Token[] {
  const tokens: Token[] = [];
  const keywords = /\b(from|import|class|def|return|if|else|elif|for|in|while|with|as|try|except|finally|raise|pass|break|continue|and|or|not|is|None|True|False)\b/g;
  const commentIdx = line.indexOf("#");
  const codePart = commentIdx >= 0 ? line.slice(0, commentIdx) : line;
  const commentPart = commentIdx >= 0 ? line.slice(commentIdx) : "";

  if (codePart.length > 0) {
    let remaining = codePart;
    while (remaining.length > 0) {
      // Try string match (double-quoted)
      const strMatchD = remaining.match(/^"([^"]*)"/);
      if (strMatchD) {
        tokens.push({ text: strMatchD[0], color: "#4ade80" });
        remaining = remaining.slice(strMatchD[0].length);
        continue;
      }
      // Try string match (single-quoted)
      const strMatchS = remaining.match(/^'([^']*)'/);
      if (strMatchS) {
        tokens.push({ text: strMatchS[0], color: "#4ade80" });
        remaining = remaining.slice(strMatchS[0].length);
        continue;
      }
      // Try keyword match
      keywords.lastIndex = 0;
      const kwMatch = remaining.match(/^(from|import|class|def|return|if|else|elif|for|in|while|with|as|try|except|finally|raise|pass|break|continue|and|or|not|is|None|True|False)\b/);
      if (kwMatch) {
        tokens.push({ text: kwMatch[0], color: "#c084fc" });
        remaining = remaining.slice(kwMatch[0].length);
        continue;
      }
      // Try function call
      const fnMatch = remaining.match(/^(\w+)(?=\()/);
      if (fnMatch && !["from", "import", "class", "def", "return", "if", "else", "elif", "for", "in", "while", "with", "as"].includes(fnMatch[0])) {
        tokens.push({ text: fnMatch[0], color: "#60a5fa" });
        remaining = remaining.slice(fnMatch[0].length);
        continue;
      }
      // Default: take one character
      tokens.push({ text: remaining[0], color: "#e4e4e7" });
      remaining = remaining.slice(1);
    }
  }

  if (commentPart.length > 0) {
    tokens.push({ text: commentPart, color: "#6b7280" });
  }

  return tokens;
}

function CodeBlock({ code }: { code: string }) {
  const lines = code.split("\n");
  return (
    <pre
      style={{
        background: "rgba(0,0,0,0.45)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: "1rem 1.25rem",
        overflowX: "auto",
        fontFamily: "var(--font-mono), monospace",
        fontSize: "0.74rem",
        lineHeight: 1.7,
        margin: 0,
      }}
    >
      {lines.map((line, i) => {
        const tokens = tokenizePython(line);
        return (
          <div key={i}>
            {tokens.length === 0 ? (
              "\u00A0"
            ) : (
              tokens.map((t, j) => (
                <span key={j} style={{ color: t.color }}>
                  {t.text}
                </span>
              ))
            )}
          </div>
        );
      })}
    </pre>
  );
}

/* ------------------------------------------------------------------ */
/*  Inline code snippet (small, one-line)                              */
/* ------------------------------------------------------------------ */

function InlineCode({ code }: { code: string }) {
  const tokens = tokenizePython(code);
  return (
    <code
      style={{
        background: "rgba(0,0,0,0.45)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 6,
        padding: "0.35rem 0.65rem",
        fontFamily: "var(--font-mono), monospace",
        fontSize: "0.72rem",
        display: "inline-block",
      }}
    >
      {tokens.map((t, j) => (
        <span key={j} style={{ color: t.color }}>
          {t.text}
        </span>
      ))}
    </code>
  );
}

/* ------------------------------------------------------------------ */
/*  Section heading helper                                             */
/* ------------------------------------------------------------------ */

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: "var(--font-mono), monospace",
        fontSize: "0.7rem",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        color: "#a1a1aa",
        marginBottom: "1rem",
      }}
    >
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Divider helper                                                     */
/* ------------------------------------------------------------------ */

function Divider() {
  return (
    <div
      style={{
        height: 1,
        background:
          "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
        margin: "1.75rem 0",
      }}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function ArchitectureWidget() {
  const [demoMode, setDemoMode] = useState(true);
  const [expandedSurface, setExpandedSurface] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const toggleDemo = useCallback(() => {
    setDemoMode((prev) => !prev);
  }, []);

  const toggleSurface = useCallback((id: string) => {
    setExpandedSurface((prev) => (prev === id ? null : id));
  }, []);

  /* ---- Colors per mode ---- */
  const demoColor = "#4ade80";
  const liveColor = "#f97316";
  const accentColor = "#38bdf8";
  const activeColor = demoMode ? demoColor : liveColor;

  return (
    <div className="widget-container s7">
      {/* ---- Label ---- */}
      <div className="widget-label">
        Interactive &middot; Architecture &amp; Demo Mode
      </div>

      {/* ================================================================ */}
      {/*  PART 1 — Client Architecture Diagram                            */}
      {/* ================================================================ */}
      <SectionHeading>Client Architecture</SectionHeading>

      {/* Toggle switch */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1.25rem",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.72rem",
            color: "#a1a1aa",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          Demo Mode
        </span>

        {/* Toggle track */}
        <button
          onClick={toggleDemo}
          aria-label={`Demo mode ${demoMode ? "on" : "off"}`}
          style={{
            position: "relative",
            width: 44,
            height: 24,
            borderRadius: 12,
            border: `1.5px solid ${activeColor}`,
            background: demoMode
              ? "rgba(74,222,128,0.18)"
              : "rgba(249,115,22,0.12)",
            cursor: "pointer",
            transition: "all 0.35s ease",
            padding: 0,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 2,
              left: demoMode ? 22 : 2,
              width: 18,
              height: 18,
              borderRadius: 9,
              background: activeColor,
              transition: "left 0.35s ease, background 0.35s ease",
            }}
          />
        </button>

        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.78rem",
            color: activeColor,
            fontWeight: 600,
            transition: "color 0.35s ease",
          }}
        >
          {demoMode ? "ON" : "OFF"}
        </span>
      </div>

      {/* Architecture diagram */}
      {mounted && (
        <div
          style={{
            background: "rgba(0,0,0,0.35)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10,
            padding: "1.5rem",
            marginBottom: "0.75rem",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* VisionClient box (always visible) */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <div
              style={{
                border: `1.5px solid ${accentColor}`,
                borderRadius: 8,
                padding: "0.6rem 1.5rem",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.82rem",
                color: accentColor,
                fontWeight: 600,
                background: "rgba(56,189,248,0.06)",
                textAlign: "center",
              }}
            >
              VisionClient
            </div>

            {/* Arrow down */}
            <svg
              width="2"
              height="28"
              viewBox="0 0 2 28"
              aria-hidden="true"
              style={{ flexShrink: 0 }}
            >
              <line
                x1="1"
                y1="0"
                x2="1"
                y2="28"
                stroke={activeColor}
                strokeWidth="1.5"
                strokeDasharray="4 3"
                style={{ transition: "stroke 0.35s ease" }}
              />
            </svg>

            {/* ---- Demo path ---- */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "0.75rem",
                opacity: demoMode ? 1 : 0,
                maxHeight: demoMode ? 300 : 0,
                overflow: "hidden",
                transition:
                  "opacity 0.4s ease, max-height 0.4s ease",
                position: demoMode ? "relative" : "absolute",
                pointerEvents: demoMode ? "auto" : "none",
              }}
            >
              <div
                style={{
                  border: `1.5px solid ${demoColor}`,
                  borderRadius: 8,
                  padding: "0.5rem 1.25rem",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.78rem",
                  color: demoColor,
                  fontWeight: 600,
                  background: "rgba(74,222,128,0.06)",
                }}
              >
                DemoClient
              </div>

              <svg
                width="2"
                height="20"
                viewBox="0 0 2 20"
                aria-hidden="true"
              >
                <line
                  x1="1"
                  y1="0"
                  x2="1"
                  y2="20"
                  stroke={demoColor}
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
              </svg>

              <div
                style={{
                  border: `1.5px solid ${demoColor}`,
                  borderRadius: 8,
                  padding: "0.5rem 1.25rem",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.72rem",
                  color: demoColor,
                  background: "rgba(74,222,128,0.06)",
                  textAlign: "center",
                  lineHeight: 1.6,
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: "0.2rem" }}>
                  Gallery Fixtures
                </div>
                <div style={{ fontSize: "0.66rem", opacity: 0.8 }}>
                  manifest.json &middot; responses/*.json
                </div>
              </div>

              <div style={{ marginTop: "0.5rem" }}>
                <InlineCode code='client = VisionClient(demo=True)' />
              </div>

              <div
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.68rem",
                  color: demoColor,
                  opacity: 0.85,
                  marginTop: "0.15rem",
                }}
              >
                No OCI credentials needed
              </div>
            </div>

            {/* ---- Live path ---- */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "0.75rem",
                opacity: demoMode ? 0 : 1,
                maxHeight: demoMode ? 0 : 300,
                overflow: "hidden",
                transition:
                  "opacity 0.4s ease, max-height 0.4s ease",
                position: demoMode ? "absolute" : "relative",
                pointerEvents: demoMode ? "none" : "auto",
              }}
            >
              <div
                style={{
                  border: `1.5px solid ${liveColor}`,
                  borderRadius: 8,
                  padding: "0.5rem 1.25rem",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.78rem",
                  color: liveColor,
                  fontWeight: 600,
                  background: "rgba(249,115,22,0.06)",
                }}
              >
                OCI SDK
              </div>

              <svg
                width="2"
                height="20"
                viewBox="0 0 2 20"
                aria-hidden="true"
              >
                <line
                  x1="1"
                  y1="0"
                  x2="1"
                  y2="20"
                  stroke={liveColor}
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
              </svg>

              {/* Cloud shape for API */}
              <div
                style={{
                  position: "relative",
                  padding: "0.6rem 1.5rem",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.78rem",
                  color: liveColor,
                  fontWeight: 600,
                  textAlign: "center",
                }}
              >
                <svg
                  style={{
                    position: "absolute",
                    top: -4,
                    left: -10,
                    width: "calc(100% + 20px)",
                    height: "calc(100% + 8px)",
                  }}
                  viewBox="0 0 180 50"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <path
                    d="M30,40 C10,40 5,30 10,22 C5,14 15,5 28,8 C35,0 55,-2 65,8 C75,2 95,0 105,8 C120,-2 145,0 152,10 C168,8 178,18 172,28 C178,35 170,42 155,40 Z"
                    fill="rgba(249,115,22,0.06)"
                    stroke={liveColor}
                    strokeWidth="1.2"
                  />
                </svg>
                <span style={{ position: "relative", zIndex: 1 }}>
                  OCI Vision API
                </span>
              </div>

              <svg
                width="2"
                height="20"
                viewBox="0 0 2 20"
                aria-hidden="true"
              >
                <line
                  x1="1"
                  y1="0"
                  x2="1"
                  y2="20"
                  stroke={liveColor}
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
              </svg>

              <div
                style={{
                  border: `1.5px solid ${liveColor}`,
                  borderRadius: 8,
                  padding: "0.5rem 1.25rem",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.72rem",
                  color: liveColor,
                  background: "rgba(249,115,22,0.06)",
                }}
              >
                ~/.oci/config
              </div>

              <div style={{ marginTop: "0.5rem" }}>
                <InlineCode code="client = VisionClient()  # uses ~/.oci/config" />
              </div>

              <div
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.68rem",
                  color: liveColor,
                  opacity: 0.85,
                  marginTop: "0.15rem",
                }}
              >
                Requires OCI API key
              </div>
            </div>
          </div>
        </div>
      )}

      <Divider />

      {/* ================================================================ */}
      {/*  PART 2 — Multi-Surface Delivery                                 */}
      {/* ================================================================ */}
      <SectionHeading>Multi-Surface Delivery</SectionHeading>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "0.75rem",
          marginBottom: "0.25rem",
        }}
      >
        {SURFACES.map((surface) => {
          const isExpanded = expandedSurface === surface.id;
          return (
            <button
              key={surface.id}
              onClick={() => toggleSurface(surface.id)}
              className={isExpanded ? "btn-mono active" : "btn-mono"}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: "0.4rem",
                padding: "0.85rem 1rem",
                background: isExpanded
                  ? "rgba(56,189,248,0.08)"
                  : "rgba(0,0,0,0.3)",
                border: `1px solid ${
                  isExpanded ? "rgba(56,189,248,0.3)" : "rgba(255,255,255,0.06)"
                }`,
                borderRadius: 8,
                cursor: "pointer",
                textAlign: "left",
                width: "100%",
                transition: "all 0.25s ease",
                fontFamily: "var(--font-mono), monospace",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  width: "100%",
                }}
              >
                <span style={{ fontSize: "1.15rem" }}>{surface.icon}</span>
                <span
                  style={{
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: isExpanded ? accentColor : "#e4e4e7",
                    transition: "color 0.25s ease",
                  }}
                >
                  {surface.title}
                </span>
              </div>

              <code
                style={{
                  fontSize: "0.65rem",
                  color: "#a1a1aa",
                  background: "rgba(0,0,0,0.3)",
                  padding: "0.2rem 0.4rem",
                  borderRadius: 4,
                  display: "block",
                  width: "100%",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {surface.snippet}
              </code>

              <span
                style={{
                  fontSize: "0.66rem",
                  color: "#a1a1aa",
                  lineHeight: 1.4,
                }}
              >
                {surface.brief}
              </span>

              {/* Expanded detail */}
              <div
                style={{
                  maxHeight: isExpanded ? 120 : 0,
                  opacity: isExpanded ? 1 : 0,
                  overflow: "hidden",
                  transition: "max-height 0.3s ease, opacity 0.3s ease",
                  width: "100%",
                }}
              >
                <div
                  style={{
                    marginTop: "0.5rem",
                    paddingTop: "0.5rem",
                    borderTop: "1px solid rgba(255,255,255,0.06)",
                    fontSize: "0.66rem",
                    color: "#a1a1aa",
                    lineHeight: 1.55,
                  }}
                >
                  {surface.detail}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <Divider />

      {/* ================================================================ */}
      {/*  PART 3 — API Usage Code Block                                   */}
      {/* ================================================================ */}
      <SectionHeading>Python API</SectionHeading>

      <CodeBlock
        code={`from oci_vision import VisionClient

client = VisionClient(demo=True)
report = client.analyze("dog_closeup.jpg")

# Individual features
labels = client.classify("dog_closeup.jpg")
objects = client.detect_objects("dog_closeup.jpg")
text = client.detect_text("sign_board.png")
faces = client.detect_faces("portrait_demo.png")
doc = client.analyze_document("invoice_demo.png")`}
      />
    </div>
  );
}
