"use client";

import { useState, useCallback, useMemo, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types & static data                                                */
/* ------------------------------------------------------------------ */

type LandmarkGroup = "eyes" | "nose" | "mouth" | "ears" | "jaw";

interface Landmark {
  name: string;
  x: number;
  y: number;
  group: LandmarkGroup;
  position: string;
}

const GROUP_META: Record<
  LandmarkGroup,
  { label: string; color: string; colorDim: string }
> = {
  eyes: { label: "Eyes", color: "#a78bfa", colorDim: "rgba(167,139,250,0.25)" },
  nose: { label: "Nose", color: "#22d3ee", colorDim: "rgba(34,211,238,0.25)" },
  mouth: { label: "Mouth", color: "#f472b6", colorDim: "rgba(244,114,182,0.25)" },
  ears: { label: "Ears", color: "#f97316", colorDim: "rgba(249,115,22,0.25)" },
  jaw: { label: "Jaw", color: "#4ade80", colorDim: "rgba(74,222,128,0.25)" },
};

const ALL_GROUPS: LandmarkGroup[] = ["eyes", "nose", "mouth", "ears", "jaw"];

const LANDMARKS: Landmark[] = [
  { name: "left_eye", x: 0.35, y: 0.38, group: "eyes", position: "upper-left" },
  { name: "right_eye", x: 0.65, y: 0.38, group: "eyes", position: "upper-right" },
  { name: "nose_tip", x: 0.5, y: 0.52, group: "nose", position: "center" },
  { name: "nose_bridge", x: 0.5, y: 0.45, group: "nose", position: "upper-center" },
  { name: "mouth_left", x: 0.38, y: 0.65, group: "mouth", position: "lower-left" },
  { name: "mouth_right", x: 0.62, y: 0.65, group: "mouth", position: "lower-right" },
  { name: "mouth_center", x: 0.5, y: 0.63, group: "mouth", position: "lower-center" },
  { name: "left_ear", x: 0.18, y: 0.45, group: "ears", position: "mid-left" },
  { name: "right_ear", x: 0.82, y: 0.45, group: "ears", position: "mid-right" },
  { name: "jaw_left", x: 0.25, y: 0.72, group: "jaw", position: "lower-left" },
  { name: "jaw_center", x: 0.5, y: 0.78, group: "jaw", position: "lower-center" },
  { name: "jaw_right", x: 0.75, y: 0.72, group: "jaw", position: "lower-right" },
];

const IMG_W = 640;
const IMG_H = 480;

const SVG_W = 320;
const SVG_H = 280;

const CONFIDENCE = 98.2;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function FaceDetectionWidget() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [activeGroups, setActiveGroups] = useState<Set<LandmarkGroup>>(
    () => new Set(ALL_GROUPS),
  );
  const [hoveredLandmark, setHoveredLandmark] = useState<string | null>(null);

  /* ---- Toggle helpers ---- */
  const toggleGroup = useCallback((group: LandmarkGroup) => {
    setActiveGroups((prev) => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setActiveGroups((prev) =>
      prev.size === ALL_GROUPS.length ? new Set<LandmarkGroup>() : new Set(ALL_GROUPS),
    );
  }, []);

  const allActive = useMemo(
    () => activeGroups.size === ALL_GROUPS.length,
    [activeGroups],
  );

  /* ---- Pixel coords for hovered landmark ---- */
  const hoveredData = useMemo(() => {
    if (!hoveredLandmark) return null;
    return LANDMARKS.find((l) => l.name === hoveredLandmark) ?? null;
  }, [hoveredLandmark]);

  /* ---- Coord table rows ---- */
  const coordRows = useMemo(
    () =>
      LANDMARKS.map((lm) => ({
        ...lm,
        px: Math.round(lm.x * IMG_W),
        py: Math.round(lm.y * IMG_H),
      })),
    [],
  );

  if (!mounted) return null;

  return (
    <div className="widget-container s4">
      {/* ---- Label ---- */}
      <div className="widget-label">Interactive &middot; Face Detection</div>

      {/* ---- Confidence ---- */}
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.78rem",
          color: "#a78bfa",
          fontWeight: 600,
          marginBottom: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#a78bfa",
            boxShadow: "0 0 6px rgba(167,139,250,0.5)",
          }}
        />
        Face detected: {CONFIDENCE}% confidence
      </div>

      {/* ---- SVG Face Visualization ---- */}
      <div
        style={{
          position: "relative",
          background: "rgba(0,0,0,0.35)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 10,
          padding: "1rem",
          marginBottom: "1.25rem",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <svg
          width={SVG_W}
          height={SVG_H}
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{ maxWidth: "100%", height: "auto" }}
        >
          {/* Bounding box — dashed purple */}
          <rect
            x={SVG_W * 0.12}
            y={SVG_H * 0.1}
            width={SVG_W * 0.76}
            height={SVG_H * 0.82}
            rx={8}
            stroke="#a78bfa"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            fill="none"
          />

          {/* Face oval */}
          <ellipse
            cx={SVG_W * 0.5}
            cy={SVG_H * 0.48}
            rx={SVG_W * 0.28}
            ry={SVG_H * 0.4}
            stroke="rgba(255,255,255,0.15)"
            strokeWidth={1.5}
            fill="rgba(255,255,255,0.02)"
          />

          {/* Eyebrows */}
          <path
            d={`M${SVG_W * 0.27},${SVG_H * 0.3} Q${SVG_W * 0.35},${SVG_H * 0.24} ${SVG_W * 0.43},${SVG_H * 0.3}`}
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1.2}
            strokeLinecap="round"
            fill="none"
          />
          <path
            d={`M${SVG_W * 0.57},${SVG_H * 0.3} Q${SVG_W * 0.65},${SVG_H * 0.24} ${SVG_W * 0.73},${SVG_H * 0.3}`}
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1.2}
            strokeLinecap="round"
            fill="none"
          />

          {/* Eye outlines */}
          <ellipse
            cx={SVG_W * 0.35}
            cy={SVG_H * 0.38}
            rx={12}
            ry={7}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
            fill="none"
          />
          <ellipse
            cx={SVG_W * 0.65}
            cy={SVG_H * 0.38}
            rx={12}
            ry={7}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
            fill="none"
          />

          {/* Nose line */}
          <path
            d={`M${SVG_W * 0.5},${SVG_H * 0.4} L${SVG_W * 0.5},${SVG_H * 0.52} Q${SVG_W * 0.46},${SVG_H * 0.55} ${SVG_W * 0.5},${SVG_H * 0.55} Q${SVG_W * 0.54},${SVG_H * 0.55} ${SVG_W * 0.5},${SVG_H * 0.52}`}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
            fill="none"
          />

          {/* Mouth outline */}
          <path
            d={`M${SVG_W * 0.38},${SVG_H * 0.65} Q${SVG_W * 0.5},${SVG_H * 0.72} ${SVG_W * 0.62},${SVG_H * 0.65}`}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
            fill="none"
          />

          {/* Ear hints */}
          <path
            d={`M${SVG_W * 0.22},${SVG_H * 0.35} Q${SVG_W * 0.16},${SVG_H * 0.45} ${SVG_W * 0.22},${SVG_H * 0.55}`}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={1}
            fill="none"
          />
          <path
            d={`M${SVG_W * 0.78},${SVG_H * 0.35} Q${SVG_W * 0.84},${SVG_H * 0.45} ${SVG_W * 0.78},${SVG_H * 0.55}`}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={1}
            fill="none"
          />

          {/* Jaw line */}
          <path
            d={`M${SVG_W * 0.25},${SVG_H * 0.6} Q${SVG_W * 0.3},${SVG_H * 0.8} ${SVG_W * 0.5},${SVG_H * 0.85} Q${SVG_W * 0.7},${SVG_H * 0.8} ${SVG_W * 0.75},${SVG_H * 0.6}`}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={1}
            fill="none"
          />

          {/* Landmark dots */}
          {LANDMARKS.map((lm) => {
            const active = activeGroups.has(lm.group);
            const isHovered = hoveredLandmark === lm.name;
            const meta = GROUP_META[lm.group];
            const cx = lm.x * SVG_W;
            const cy = lm.y * SVG_H;

            return (
              <g key={lm.name}>
                {/* Hover ring */}
                {isHovered && active && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={10}
                    fill="none"
                    stroke={meta.color}
                    strokeWidth={1}
                    opacity={0.5}
                  />
                )}
                <circle
                  cx={cx}
                  cy={cy}
                  r={active ? (isHovered ? 6 : 4.5) : 3}
                  fill={active ? meta.color : meta.colorDim}
                  stroke={active && isHovered ? "#fff" : "none"}
                  strokeWidth={1.5}
                  style={{
                    cursor: "pointer",
                    transition: "r 0.15s, fill 0.15s",
                  }}
                  onMouseEnter={() => setHoveredLandmark(lm.name)}
                  onMouseLeave={() => setHoveredLandmark(null)}
                />
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {hoveredData && (
          <div
            style={{
              position: "absolute",
              left:
                hoveredData.x * SVG_W + 16 > SVG_W * 0.65
                  ? "auto"
                  : `calc(50% - ${SVG_W / 2}px + ${hoveredData.x * SVG_W + 18}px)`,
              right:
                hoveredData.x * SVG_W + 16 > SVG_W * 0.65
                  ? `calc(50% - ${SVG_W / 2}px + ${SVG_W - hoveredData.x * SVG_W + 18}px)`
                  : "auto",
              top: `${hoveredData.y * SVG_H + 16}px`,
              background: "#1e1e26",
              border: `1px solid ${GROUP_META[hoveredData.group].color}44`,
              borderRadius: 8,
              padding: "0.5rem 0.75rem",
              zIndex: 50,
              pointerEvents: "none",
              animation: "fadeSlideIn 0.15s ease-out both",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.78rem",
                color: GROUP_META[hoveredData.group].color,
                fontWeight: 600,
                marginBottom: "0.3rem",
              }}
            >
              {hoveredData.name}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.68rem",
                color: "#a1a1aa",
                lineHeight: 1.7,
              }}
            >
              <div>
                Normalized:{" "}
                <span style={{ color: "#e4e4e7" }}>
                  ({hoveredData.x.toFixed(2)}, {hoveredData.y.toFixed(2)})
                </span>
              </div>
              <div>
                Pixel ({IMG_W}&times;{IMG_H}):{" "}
                <span style={{ color: "#e4e4e7" }}>
                  ({Math.round(hoveredData.x * IMG_W)},{" "}
                  {Math.round(hoveredData.y * IMG_H)})
                </span>
              </div>
              <div>
                Position:{" "}
                <span style={{ color: "#e4e4e7" }}>{hoveredData.position}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ---- Group toggle buttons ---- */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.4rem",
          marginBottom: "1.25rem",
        }}
      >
        {ALL_GROUPS.map((group) => {
          const meta = GROUP_META[group];
          const active = activeGroups.has(group);
          return (
            <button
              key={group}
              className={`btn-mono${active ? " active" : ""}`}
              onClick={() => toggleGroup(group)}
              style={{
                borderColor: active ? `${meta.color}55` : undefined,
                color: active ? meta.color : undefined,
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: active ? meta.color : "rgba(255,255,255,0.15)",
                  marginRight: "0.4rem",
                  verticalAlign: "middle",
                  transition: "background 0.15s",
                }}
              />
              {meta.label}
            </button>
          );
        })}
        <button
          className={`btn-mono${allActive ? " active" : ""}`}
          onClick={toggleAll}
        >
          All
        </button>
      </div>

      {/* ---- Divider ---- */}
      <div
        style={{
          height: 1,
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
          margin: "0 0 1.25rem",
        }}
      />

      {/* ---- Coordinate Reference Panel ---- */}
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
        Coordinate Reference
      </div>

      <div
        style={{
          background: "rgba(0,0,0,0.3)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        {/* Header row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 0,
            padding: "0.5rem 0.75rem",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.65rem",
              color: "#a1a1aa",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Landmark
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.65rem",
              color: "#a1a1aa",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              textAlign: "center",
            }}
          >
            Normalized (0-1)
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.65rem",
              color: "#a1a1aa",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              textAlign: "right",
            }}
          >
            Pixel ({IMG_W}&times;{IMG_H})
          </span>
        </div>

        {/* Data rows */}
        {coordRows.map((row) => {
          const isHovered = hoveredLandmark === row.name;
          const meta = GROUP_META[row.group];
          const active = activeGroups.has(row.group);

          return (
            <div
              key={row.name}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: 0,
                padding: "0.35rem 0.75rem",
                borderBottom: "1px solid rgba(255,255,255,0.03)",
                background: isHovered
                  ? "rgba(167,139,250,0.08)"
                  : "transparent",
                opacity: active ? 1 : 0.3,
                transition: "background 0.15s, opacity 0.2s",
              }}
              onMouseEnter={() => setHoveredLandmark(row.name)}
              onMouseLeave={() => setHoveredLandmark(null)}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.72rem",
                  color: isHovered ? meta.color : "#e4e4e7",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  transition: "color 0.15s",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: meta.color,
                    flexShrink: 0,
                  }}
                />
                {row.name}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.72rem",
                  color: isHovered ? "#e4e4e7" : "#a1a1aa",
                  textAlign: "center",
                  transition: "color 0.15s",
                }}
              >
                ({row.x.toFixed(2)}, {row.y.toFixed(2)})
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.72rem",
                  color: isHovered ? "#e4e4e7" : "#a1a1aa",
                  textAlign: "right",
                  transition: "color 0.15s",
                }}
              >
                ({row.px}, {row.py})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
