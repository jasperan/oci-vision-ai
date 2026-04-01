"use client";

import { useState, useCallback, useMemo, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Static data — no randomness, no hydration mismatches               */
/* ------------------------------------------------------------------ */

interface OcrWord {
  text: string;
  confidence: number;
}

interface OcrLine {
  words: OcrWord[];
  confidence: number;
}

const SIGN_LINES: OcrLine[] = [
  {
    words: [
      { text: "WELCOME", confidence: 0.98 },
      { text: "TO", confidence: 0.96 },
    ],
    confidence: 0.97,
  },
  {
    words: [
      { text: "ORACLE", confidence: 0.97 },
      { text: "CLOUD", confidence: 0.94 },
    ],
    confidence: 0.95,
  },
  {
    words: [
      { text: "INNOVATION", confidence: 0.96 },
      { text: "LAB", confidence: 0.93 },
    ],
    confidence: 0.94,
  },
  {
    words: [
      { text: "Open", confidence: 0.91 },
      { text: "Mon-Fri", confidence: 0.88 },
      { text: "9:00-17:00", confidence: 0.85 },
    ],
    confidence: 0.88,
  },
  {
    words: [
      { text: "Building", confidence: 0.92 },
      { text: "42,", confidence: 0.89 },
      { text: "Floor", confidence: 0.93 },
      { text: "3", confidence: 0.90 },
    ],
    confidence: 0.91,
  },
];

const STAGES = [
  { id: 1, label: "Raw Image", icon: "\uD83D\uDDBC\uFE0F" },
  { id: 2, label: "Line Detection", icon: "\uD83D\uDD0D" },
  { id: 3, label: "Word Segmentation", icon: "\u2702\uFE0F" },
  { id: 4, label: "Character Recognition", icon: "\uD83C\uDD70\uFE0F" },
] as const;

/* Visual layout for the sign — pre-computed positions (percentages) */
const LINE_LAYOUT = [
  { top: 10, fontSize: "1.1rem", fontWeight: 700, letterSpacing: "0.18em" },
  { top: 26, fontSize: "1.35rem", fontWeight: 800, letterSpacing: "0.22em" },
  { top: 44, fontSize: "1.1rem", fontWeight: 700, letterSpacing: "0.18em" },
  { top: 64, fontSize: "0.78rem", fontWeight: 400, letterSpacing: "0.04em" },
  { top: 78, fontSize: "0.72rem", fontWeight: 400, letterSpacing: "0.04em" },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function OcrWidget() {
  const [mounted, setMounted] = useState(false);
  const [stage, setStage] = useState(1);
  const [autoPlay, setAutoPlay] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  /* Auto-play timer */
  useEffect(() => {
    if (!autoPlay) return;
    const timer = setInterval(() => {
      setStage((prev) => (prev >= 4 ? 1 : prev + 1));
    }, 2000);
    return () => clearInterval(timer);
  }, [autoPlay]);

  const handleStep = useCallback(() => {
    setStage((prev) => (prev >= 4 ? 4 : prev + 1));
  }, []);

  const handleReset = useCallback(() => {
    setStage(1);
    setAutoPlay(false);
  }, []);

  const toggleAutoPlay = useCallback(() => {
    setAutoPlay((prev) => !prev);
  }, []);

  const fullText = useMemo(
    () => SIGN_LINES.map((l) => l.words.map((w) => w.text).join(" ")).join("\n"),
    [],
  );

  const currentStage = STAGES[stage - 1];

  if (!mounted) {
    return (
      <div className="widget-container s3">
        <div className="widget-label">Interactive &middot; Text / OCR</div>
        <div style={{ height: 400 }} />
      </div>
    );
  }

  return (
    <div className="widget-container s3">
      {/* ---- Label ---- */}
      <div className="widget-label">Interactive &middot; Text / OCR</div>

      {/* ---- Progress indicator ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.78rem",
            color: "#4ade80",
            fontWeight: 600,
          }}
        >
          Stage {stage} of 4 &mdash; {currentStage.label}
        </span>

        {/* Stage dots */}
        <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
          {STAGES.map((s) => (
            <div
              key={s.id}
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background:
                  s.id < stage
                    ? "#4ade80"
                    : s.id === stage
                      ? "rgba(74,222,128,0.5)"
                      : "rgba(255,255,255,0.1)",
                border:
                  s.id === stage
                    ? "2px solid #4ade80"
                    : "2px solid transparent",
                transition: "all 0.3s",
              }}
            />
          ))}
        </div>
      </div>

      {/* ---- Sign visualization ---- */}
      <div
        style={{
          position: "relative",
          background: "rgba(0,0,0,0.5)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 10,
          padding: "2rem 1.5rem",
          marginBottom: "1rem",
          minHeight: 220,
          overflow: "hidden",
        }}
      >
        {/* Subtle sign border accent */}
        <div
          style={{
            position: "absolute",
            inset: 6,
            border: "1px solid rgba(74,222,128,0.08)",
            borderRadius: 6,
            pointerEvents: "none",
          }}
        />

        {/* Sign text lines */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.6rem",
            position: "relative",
          }}
        >
          {SIGN_LINES.map((line, li) => {
            const layout = LINE_LAYOUT[li];
            const lineText = line.words.map((w) => w.text).join(" ");
            const isLargeLine = li < 3;

            return (
              <div
                key={li}
                style={{
                  position: "relative",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: li < 3 ? "0.5rem" : "0.35rem",
                  padding:
                    stage >= 2
                      ? "0.3rem 0.6rem"
                      : "0.3rem 0.6rem",
                  transition: "all 0.4s ease",
                }}
              >
                {/* Line bounding box — stage 2+ */}
                {stage >= 2 && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      border: "1.5px solid rgba(74,222,128,0.5)",
                      borderRadius: 4,
                      background: "rgba(74,222,128,0.04)",
                      animation: "fadeIn 0.4s ease-out both",
                      animationDelay: `${li * 100}ms`,
                    }}
                  />
                )}

                {/* Words */}
                {line.words.map((word, wi) => (
                  <span
                    key={wi}
                    style={{
                      position: "relative",
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: layout.fontSize,
                      fontWeight: layout.fontWeight,
                      letterSpacing: layout.letterSpacing,
                      color: isLargeLine ? "#e4e4e7" : "#a1a1aa",
                      padding:
                        stage >= 3
                          ? "0.1rem 0.3rem"
                          : undefined,
                      transition: "all 0.3s ease",
                      zIndex: 1,
                    }}
                  >
                    {/* Word bounding box — stage 3+ */}
                    {stage >= 3 && (
                      <span
                        style={{
                          position: "absolute",
                          inset: 0,
                          border: "1px solid rgba(74,222,128,0.7)",
                          borderRadius: 3,
                          background: "rgba(74,222,128,0.06)",
                          animation: "fadeIn 0.3s ease-out both",
                          animationDelay: `${li * 100 + wi * 60}ms`,
                        }}
                      />
                    )}

                    {word.text}

                    {/* Confidence badge — stage 4 */}
                    {stage >= 4 && (
                      <span
                        style={{
                          position: "absolute",
                          top: -14,
                          right: -4,
                          fontFamily: "var(--font-mono), monospace",
                          fontSize: "0.55rem",
                          color: "#4ade80",
                          background: "rgba(0,0,0,0.7)",
                          padding: "1px 4px",
                          borderRadius: 3,
                          fontWeight: 600,
                          whiteSpace: "nowrap",
                          animation: "fadeIn 0.3s ease-out both",
                          animationDelay: `${li * 80 + wi * 40 + 200}ms`,
                        }}
                      >
                        {word.confidence.toFixed(2)}
                      </span>
                    )}
                  </span>
                ))}

                {/* Line label — stage 2 */}
                {stage >= 2 && stage < 3 && (
                  <span
                    style={{
                      position: "absolute",
                      left: -30,
                      top: "50%",
                      transform: "translateY(-50%)",
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "0.55rem",
                      color: "rgba(74,222,128,0.6)",
                      whiteSpace: "nowrap",
                      animation: "fadeIn 0.3s ease-out both",
                      animationDelay: `${li * 100 + 200}ms`,
                    }}
                  >
                    L{li + 1}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* File label */}
        <div
          style={{
            textAlign: "center",
            marginTop: "1rem",
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.68rem",
            color: "#71717a",
          }}
        >
          sign_board.png
        </div>
      </div>

      {/* ---- Controls ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <button
          className="btn-mono"
          onClick={handleStep}
          disabled={stage >= 4}
          style={{
            opacity: stage >= 4 ? 0.4 : 1,
            cursor: stage >= 4 ? "not-allowed" : "pointer",
          }}
        >
          Step &rarr;
        </button>
        <button className="btn-mono" onClick={handleReset}>
          Reset
        </button>
        <button
          className={`btn-mono${autoPlay ? " active" : ""}`}
          onClick={toggleAutoPlay}
        >
          {autoPlay ? "Stop" : "Auto Play"}
        </button>
      </div>

      {/* ---- Pipeline stages (how it works) ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          overflowX: "auto",
          paddingBottom: "0.25rem",
          marginBottom: "1.25rem",
        }}
      >
        {STAGES.map((s, i) => (
          <div
            key={s.id}
            style={{ display: "flex", alignItems: "center", flexShrink: 0 }}
          >
            <div
              className={`pipeline-stage${
                s.id === stage
                  ? " active"
                  : s.id < stage
                    ? " completed"
                    : ""
              }`}
              style={{
                borderColor:
                  s.id === stage
                    ? "rgba(74,222,128,0.4)"
                    : s.id < stage
                      ? "rgba(74,222,128,0.25)"
                      : undefined,
                background:
                  s.id === stage
                    ? "rgba(74,222,128,0.06)"
                    : s.id < stage
                      ? "rgba(74,222,128,0.03)"
                      : undefined,
              }}
            >
              <span style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}>
                {s.icon}
              </span>
              <span
                style={{
                  fontSize: "0.68rem",
                  color: s.id <= stage ? "#4ade80" : "#a1a1aa",
                  lineHeight: 1.3,
                  transition: "color 0.3s",
                }}
              >
                {s.label}
              </span>
            </div>

            {i < STAGES.length - 1 && (
              <span
                style={{
                  color:
                    i < stage - 1
                      ? "rgba(74,222,128,0.5)"
                      : "rgba(255,255,255,0.15)",
                  fontSize: "1.1rem",
                  margin: "0 0.35rem",
                  flexShrink: 0,
                  transition: "color 0.3s",
                }}
                aria-hidden="true"
              >
                &rarr;
              </span>
            )}
          </div>
        ))}
      </div>

      {/* ---- Divider ---- */}
      <div
        style={{
          height: 1,
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
          margin: "0 0 1.25rem 0",
        }}
      />

      {/* ---- Hierarchical extraction result ---- */}
      {stage >= 2 && (
        <div style={{ marginBottom: "1.25rem" }}>
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              color: "#a1a1aa",
              marginBottom: "0.75rem",
            }}
          >
            Extraction Result &mdash; Lines ({SIGN_LINES.length} detected)
          </div>

          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.75rem",
              lineHeight: 1.8,
            }}
          >
            {SIGN_LINES.map((line, li) => {
              const lineText = line.words.map((w) => w.text).join(" ");
              const isLast = li === SIGN_LINES.length - 1;
              const linePrefix = isLast ? "\u2514" : "\u251C";
              const childPrefix = isLast ? "\u00A0\u00A0\u00A0" : "\u2502\u00A0\u00A0";

              return (
                <div
                  key={li}
                  style={{
                    animation: "fadeSlideIn 0.3s ease-out both",
                    animationDelay: `${li * 80}ms`,
                  }}
                >
                  {/* Line entry */}
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ color: "#71717a" }}>{linePrefix}\u2500\u2500</span>
                    <span style={{ color: "#e4e4e7" }}>
                      Line {li + 1}:{" "}
                      <span style={{ color: "#4ade80" }}>
                        &quot;{lineText}&quot;
                      </span>
                    </span>
                    <ConfidencePill value={line.confidence} />
                  </div>

                  {/* Word entries — stage 3+ */}
                  {stage >= 3 &&
                    line.words.map((word, wi) => {
                      const isLastWord = wi === line.words.length - 1;
                      const wordPrefix = isLastWord ? "\u2514" : "\u251C";

                      return (
                        <div
                          key={wi}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                            animation: "fadeSlideIn 0.25s ease-out both",
                            animationDelay: `${li * 80 + wi * 50 + 100}ms`,
                          }}
                        >
                          <span style={{ color: "#71717a" }}>
                            {childPrefix}{wordPrefix}\u2500\u2500
                          </span>
                          <span style={{ color: "#a1a1aa" }}>
                            Word:{" "}
                            <span style={{ color: "#86efac" }}>
                              &quot;{word.text}&quot;
                            </span>
                          </span>
                          <ConfidencePill value={word.confidence} />
                        </div>
                      );
                    })}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ---- Extracted text output ---- */}
      {stage >= 4 && (
        <div>
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              color: "#a1a1aa",
              marginBottom: "0.75rem",
            }}
          >
            Extracted Text
          </div>
          <div className="code-block">
            <pre
              style={{
                margin: 0,
                color: "#86efac",
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.8rem",
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
              }}
            >
              {fullText}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Confidence pill sub-component                                      */
/* ------------------------------------------------------------------ */

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.3rem",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.65rem",
          color: "#a1a1aa",
        }}
      >
        ({value.toFixed(2)})
      </span>
      {/* Mini confidence bar */}
      <span
        style={{
          display: "inline-block",
          width: 40,
          height: 4,
          borderRadius: 2,
          background: "rgba(255,255,255,0.06)",
          overflow: "hidden",
          verticalAlign: "middle",
        }}
      >
        <span
          className="confidence-bar"
          style={{
            display: "block",
            width: `${pct}%`,
            height: "100%",
            borderRadius: 2,
            background:
              value >= 0.9
                ? "linear-gradient(90deg, #4ade80, #86efac)"
                : value >= 0.8
                  ? "linear-gradient(90deg, #4ade80, #a7f3d0)"
                  : "linear-gradient(90deg, #facc15, #fde047)",
          }}
        />
      </span>
    </span>
  );
}
