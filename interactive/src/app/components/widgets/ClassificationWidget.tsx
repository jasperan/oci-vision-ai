"use client";

import { useState, useCallback, useMemo } from "react";

/* ------------------------------------------------------------------ */
/*  Static data — no randomness, no hydration mismatches               */
/* ------------------------------------------------------------------ */

interface ClassificationLabel {
  name: string;
  confidence: number;
}

const LABELS: ClassificationLabel[] = [
  { name: "Golden Retriever", confidence: 0.94 },
  { name: "Dog", confidence: 0.91 },
  { name: "Domestic Animal", confidence: 0.87 },
  { name: "Pet", confidence: 0.83 },
  { name: "Outdoor", confidence: 0.62 },
  { name: "Mammal", confidence: 0.58 },
  { name: "Canine", confidence: 0.52 },
  { name: "Park", confidence: 0.31 },
  { name: "Grass", confidence: 0.24 },
];

const PIPELINE_STAGES = [
  { label: "Image" },
  { label: "Feature extraction" },
  { label: "Label prediction" },
  { label: "Confidence scoring" },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ClassificationWidget() {
  const [threshold, setThreshold] = useState(0.5);

  const handleThreshold = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setThreshold(Math.round(parseFloat(e.target.value) * 100) / 100);
    },
    [],
  );

  const labelsAbove = useMemo(
    () => LABELS.filter((l) => l.confidence >= threshold).length,
    [threshold],
  );

  return (
    <div className="widget-container s1">
      {/* ---- Label ---- */}
      <div className="widget-label">Interactive &middot; Image Classification</div>

      {/* ---- Image placeholder ---- */}
      <div
        style={{
          background: "rgba(0,0,0,0.35)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 10,
          padding: "2.5rem 1.5rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.75rem",
          marginBottom: "1.5rem",
        }}
      >
        {/* simple dog silhouette icon */}
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <rect
            x="2"
            y="2"
            width="60"
            height="60"
            rx="12"
            stroke="rgba(255,255,255,0.16)"
            strokeWidth="1.5"
            fill="rgba(255,255,255,0.02)"
          />
          <path
            d="M20 44c0-6 4-12 12-12s12 6 12 12"
            stroke="#a8a39b"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="32" cy="26" r="7" stroke="#a8a39b" strokeWidth="2" />
          <circle cx="29" cy="25" r="1.2" fill="#a8a39b" />
          <circle cx="35" cy="25" r="1.2" fill="#a8a39b" />
          <path
            d="M24 19c-3-5-7-4-8-1s2 5 4 5"
            stroke="#a8a39b"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path
            d="M40 19c3-5 7-4 8-1s-2 5-4 5"
            stroke="#a8a39b"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.75rem",
            color: "#a8a39b",
            letterSpacing: "0.02em",
          }}
        >
          dog_closeup.jpg
        </span>
      </div>

      {/* ---- Threshold slider ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "0.5rem",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.72rem",
            color: "#a8a39b",
            flexShrink: 0,
          }}
        >
          Threshold
        </span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={threshold}
          onChange={handleThreshold}
          aria-label="Confidence threshold"
          style={{ flex: 1, minWidth: 120 }}
        />
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.85rem",
            color: "#ece9e4",
            fontVariantNumeric: "tabular-nums",
            minWidth: "2.5rem",
            textAlign: "right",
          }}
        >
          {threshold.toFixed(2)}
        </span>
      </div>

      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.7rem",
          color: "#a8a39b",
          marginBottom: "1.25rem",
        }}
      >
        {labelsAbove} label{labelsAbove !== 1 ? "s" : ""} above threshold
      </div>

      {/* ---- Classification labels ---- */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {LABELS.map((label, index) => {
          const above = label.confidence >= threshold;
          const pct = Math.round(label.confidence * 100);
          const isTop = index === 0;
          return (
            <div
              key={label.name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                opacity: above ? 1 : 0.2,
                transition: "opacity 160ms cubic-bezier(0.22, 1, 0.36, 1)",
              }}
            >
              {/* Label name */}
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.78rem",
                  color: "#ece9e4",
                  width: 140,
                  flexShrink: 0,
                  textAlign: "right",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {label.name}
              </span>

              {/* Bar track */}
              <div
                style={{
                  flex: 1,
                  height: 6,
                  borderRadius: 3,
                  background: "rgba(255,255,255,0.06)",
                  overflow: "hidden",
                  position: "relative",
                }}
              >
                <div
                  className="confidence-bar"
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    borderRadius: 3,
                    background: isTop ? "#c74634" : "#8f887e",
                  }}
                />
              </div>

              {/* Confidence value */}
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.75rem",
                  color: isTop ? "#c74634" : "#a8a39b",
                  fontVariantNumeric: "tabular-nums",
                  minWidth: "2.5rem",
                  textAlign: "right",
                  transition: "color 160ms cubic-bezier(0.22, 1, 0.36, 1)",
                }}
              >
                {label.confidence.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>

      {/* ---- Divider ---- */}
      <div
        style={{
          height: 1,
          background: "rgba(255,255,255,0.08)",
          margin: "1.5rem 0",
        }}
      />

      {/* ---- How it works ---- */}
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.75rem",
          color: "#a8a39b",
          marginBottom: "1rem",
        }}
      >
        How it works
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          overflowX: "auto",
          paddingBottom: "0.25rem",
        }}
      >
        {PIPELINE_STAGES.map((stage, i) => (
          <div
            key={stage.label}
            style={{ display: "flex", alignItems: "center", flexShrink: 0 }}
          >
            <div className="pipeline-stage">
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.7rem",
                  color: "#77726a",
                  marginBottom: "0.25rem",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#a8a39b",
                  lineHeight: 1.3,
                }}
              >
                {stage.label}
              </span>
            </div>

            {i < PIPELINE_STAGES.length - 1 && (
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#77726a"
                strokeWidth="1.5"
                style={{ margin: "0 0.35rem", flexShrink: 0 }}
                aria-hidden="true"
              >
                <path d="m9 18 6-6-6-6" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
