"use client";

import { useState, useCallback, useMemo, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DetectedObject {
  label: string;
  confidence: number;
  /** Normalized coords: [x1, y1, x2, y2] in 0..1 */
  bbox: [number, number, number, number];
  color: string;
}

interface DragRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SCENE_OBJECTS: DetectedObject[] = [
  { label: "Dog", confidence: 0.96, bbox: [0.15, 0.3, 0.45, 0.85], color: "#22d3ee" },
  { label: "Person", confidence: 0.93, bbox: [0.55, 0.1, 0.8, 0.9], color: "#4ade80" },
  { label: "Ball", confidence: 0.88, bbox: [0.4, 0.7, 0.5, 0.82], color: "#f97316" },
  { label: "Tree", confidence: 0.91, bbox: [0.82, 0.05, 0.98, 0.7], color: "#a78bfa" },
];

const SVG_W = 640;
const SVG_H = 360;

const IOU_W = 400;
const IOU_H = 240;

/* ------------------------------------------------------------------ */
/*  Helper: IoU calculation                                            */
/* ------------------------------------------------------------------ */

function computeIoU(a: DragRect, b: DragRect): number {
  const x1 = Math.max(a.x, b.x);
  const y1 = Math.max(a.y, b.y);
  const x2 = Math.min(a.x + a.w, b.x + b.w);
  const y2 = Math.min(a.y + a.h, b.y + b.h);

  const interW = Math.max(0, x2 - x1);
  const interH = Math.max(0, y2 - y1);
  const interArea = interW * interH;

  const areaA = a.w * a.h;
  const areaB = b.w * b.h;
  const unionArea = areaA + areaB - interArea;

  if (unionArea <= 0) return 0;
  return interArea / unionArea;
}

function getIntersectionRect(
  a: DragRect,
  b: DragRect,
): { x: number; y: number; w: number; h: number } | null {
  const x1 = Math.max(a.x, b.x);
  const y1 = Math.max(a.y, b.y);
  const x2 = Math.min(a.x + a.w, b.x + b.w);
  const y2 = Math.min(a.y + a.h, b.y + b.h);

  const w = Math.max(0, x2 - x1);
  const h = Math.max(0, y2 - y1);

  if (w === 0 || h === 0) return null;
  return { x: x1, y: y1, w, h };
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ObjectDetectionWidget() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* Toggle states */
  const [showLabels, setShowLabels] = useState(true);
  const [showCoords, setShowCoords] = useState(false);
  const [showIoU, setShowIoU] = useState(true);

  /* Hover state for bounding boxes */
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  /* IoU drag state */
  const [rectA, setRectA] = useState<DragRect>({ x: 60, y: 50, w: 140, h: 120 });
  const [rectB, setRectB] = useState<DragRect>({ x: 160, y: 80, w: 140, h: 120 });
  const [dragging, setDragging] = useState<"A" | "B" | null>(null);
  const dragOffset = useRef<{ dx: number; dy: number }>({ dx: 0, dy: 0 });
  const iouSvgRef = useRef<SVGSVGElement | null>(null);

  /* Memoized IoU value */
  const iouValue = useMemo(() => computeIoU(rectA, rectB), [rectA, rectB]);
  const intersection = useMemo(() => getIntersectionRect(rectA, rectB), [rectA, rectB]);

  /* ---- Scene grid lines ---- */
  const gridLines = useMemo(() => {
    const lines: { x1: number; y1: number; x2: number; y2: number }[] = [];
    for (let x = 0; x <= SVG_W; x += 40) lines.push({ x1: x, y1: 0, x2: x, y2: SVG_H });
    for (let y = 0; y <= SVG_H; y += 40) lines.push({ x1: 0, y1: y, x2: SVG_W, y2: y });
    return lines;
  }, []);

  /* ---- Scene objects (pixel-space) ---- */
  const sceneBoxes = useMemo(
    () =>
      SCENE_OBJECTS.map((obj) => {
        const x = obj.bbox[0] * SVG_W;
        const y = obj.bbox[1] * SVG_H;
        const w = (obj.bbox[2] - obj.bbox[0]) * SVG_W;
        const h = (obj.bbox[3] - obj.bbox[1]) * SVG_H;
        return { ...obj, px: { x, y, w, h } };
      }),
    [],
  );

  /* ---- Scene filler shapes (simple park icons) ---- */
  const parkShapes = useMemo(() => {
    /* Simplified scene backdrop shapes */
    return (
      <g opacity={0.35}>
        {/* Ground */}
        <rect x={0} y={SVG_H * 0.78} width={SVG_W} height={SVG_H * 0.22} fill="#1a2e1a" rx={0} />
        {/* Sky gradient line */}
        <line x1={0} y1={SVG_H * 0.78} x2={SVG_W} y2={SVG_H * 0.78} stroke="#2a3e2a" strokeWidth={1} />
        {/* Sun */}
        <circle cx={SVG_W * 0.12} cy={SVG_H * 0.12} r={18} fill="#facc15" opacity={0.5} />
        {/* Clouds */}
        <ellipse cx={SVG_W * 0.35} cy={SVG_H * 0.1} rx={40} ry={12} fill="#334155" opacity={0.4} />
        <ellipse cx={SVG_W * 0.65} cy={SVG_H * 0.15} rx={30} ry={10} fill="#334155" opacity={0.3} />
        {/* Dog silhouette */}
        <ellipse cx={SVG_W * 0.3} cy={SVG_H * 0.65} rx={35} ry={22} fill="#4a3728" opacity={0.7} />
        <ellipse cx={SVG_W * 0.25} cy={SVG_H * 0.55} rx={14} ry={12} fill="#4a3728" opacity={0.7} />
        <rect x={SVG_W * 0.2} y={SVG_H * 0.72} width={6} height={28} rx={2} fill="#4a3728" opacity={0.7} />
        <rect x={SVG_W * 0.35} y={SVG_H * 0.72} width={6} height={28} rx={2} fill="#4a3728" opacity={0.7} />
        {/* Person silhouette */}
        <circle cx={SVG_W * 0.675} cy={SVG_H * 0.18} r={16} fill="#3b4a6b" opacity={0.7} />
        <rect x={SVG_W * 0.65} y={SVG_H * 0.25} width={30} height={70} rx={6} fill="#3b4a6b" opacity={0.7} />
        <rect x={SVG_W * 0.655} y={SVG_H * 0.65} width={12} height={50} rx={3} fill="#3b4a6b" opacity={0.7} />
        <rect x={SVG_W * 0.69} y={SVG_H * 0.65} width={12} height={50} rx={3} fill="#3b4a6b" opacity={0.7} />
        {/* Ball */}
        <circle cx={SVG_W * 0.45} cy={SVG_H * 0.76} r={12} fill="#c2410c" opacity={0.7} />
        {/* Tree */}
        <rect x={SVG_W * 0.895} y={SVG_H * 0.4} width={12} height={100} rx={3} fill="#5c3a1e" opacity={0.7} />
        <ellipse cx={SVG_W * 0.9} cy={SVG_H * 0.28} rx={28} ry={38} fill="#2d5a2d" opacity={0.7} />
      </g>
    );
  }, []);

  /* ---- IoU drag handlers ---- */
  const getSvgPoint = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const svg = iouSvgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      const scaleX = IOU_W / rect.width;
      const scaleY = IOU_H / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    },
    [],
  );

  const handleIoUMouseDown = useCallback(
    (which: "A" | "B", e: React.MouseEvent<SVGRectElement>) => {
      e.preventDefault();
      const pt = getSvgPoint(e as unknown as React.MouseEvent<SVGSVGElement>);
      const r = which === "A" ? rectA : rectB;
      dragOffset.current = { dx: pt.x - r.x, dy: pt.y - r.y };
      setDragging(which);
    },
    [getSvgPoint, rectA, rectB],
  );

  const handleIoUMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!dragging) return;
      const pt = getSvgPoint(e);
      const nx = Math.max(0, Math.min(IOU_W - (dragging === "A" ? rectA.w : rectB.w), pt.x - dragOffset.current.dx));
      const ny = Math.max(0, Math.min(IOU_H - (dragging === "A" ? rectA.h : rectB.h), pt.y - dragOffset.current.dy));
      if (dragging === "A") setRectA((prev) => ({ ...prev, x: nx, y: ny }));
      else setRectB((prev) => ({ ...prev, x: nx, y: ny }));
    },
    [dragging, getSvgPoint, rectA.w, rectA.h, rectB.w, rectB.h],
  );

  const handleIoUMouseUp = useCallback(() => setDragging(null), []);

  /* ---- Tooltip position for hovered scene object ---- */
  const hoveredObj = hoveredIdx !== null ? sceneBoxes[hoveredIdx] : null;

  /* ---- Render ---- */
  if (!mounted) {
    return (
      <div className="widget-container s2">
        <div className="widget-label">Interactive &middot; Object Detection</div>
        <div style={{ height: 400 }} />
      </div>
    );
  }

  return (
    <div className="widget-container s2">
      <div className="widget-label">Interactive &middot; Object Detection</div>

      {/* ---- Toggle buttons ---- */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <button
          className={`btn-mono${showLabels ? " active" : ""}`}
          onClick={() => setShowLabels((v) => !v)}
        >
          {showLabels ? "\u2713 " : ""}Show Labels
        </button>
        <button
          className={`btn-mono${showCoords ? " active" : ""}`}
          onClick={() => setShowCoords((v) => !v)}
        >
          {showCoords ? "\u2713 " : ""}Show Coordinates
        </button>
        <button
          className={`btn-mono${showIoU ? " active" : ""}`}
          onClick={() => setShowIoU((v) => !v)}
        >
          {showIoU ? "\u2713 " : ""}Show IoU Demo
        </button>
      </div>

      {/* ================================================================ */}
      {/*  Part 1 — Bounding Box Visualization                             */}
      {/* ================================================================ */}
      <div style={{ position: "relative" }}>
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          style={{
            width: "100%",
            maxWidth: SVG_W,
            background: "#0d0e14",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.06)",
            display: "block",
          }}
        >
          {/* Grid */}
          {gridLines.map((l, i) => (
            <line
              key={i}
              x1={l.x1}
              y1={l.y1}
              x2={l.x2}
              y2={l.y2}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth={0.5}
            />
          ))}

          {/* Park scene shapes */}
          {parkShapes}

          {/* Bounding boxes */}
          {sceneBoxes.map((obj, idx) => {
            const isHovered = hoveredIdx === idx;
            return (
              <g
                key={obj.label}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
                style={{ cursor: "pointer" }}
              >
                {/* Highlight fill on hover */}
                {isHovered && (
                  <rect
                    x={obj.px.x}
                    y={obj.px.y}
                    width={obj.px.w}
                    height={obj.px.h}
                    rx={3}
                    fill={obj.color}
                    opacity={0.08}
                    className="animate-fade-in"
                  />
                )}

                {/* Bounding box outline */}
                <rect
                  x={obj.px.x}
                  y={obj.px.y}
                  width={obj.px.w}
                  height={obj.px.h}
                  rx={3}
                  fill="none"
                  stroke={obj.color}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  strokeDasharray={isHovered ? "none" : "none"}
                  opacity={isHovered ? 1 : 0.7}
                  style={{ transition: "all 0.15s" }}
                />

                {/* Corner markers */}
                {[
                  [obj.px.x, obj.px.y],
                  [obj.px.x + obj.px.w, obj.px.y],
                  [obj.px.x, obj.px.y + obj.px.h],
                  [obj.px.x + obj.px.w, obj.px.y + obj.px.h],
                ].map(([cx, cy], ci) => (
                  <circle
                    key={ci}
                    cx={cx}
                    cy={cy}
                    r={isHovered ? 3 : 2}
                    fill={obj.color}
                    opacity={isHovered ? 1 : 0.6}
                    style={{ transition: "all 0.15s" }}
                  />
                ))}

                {/* Label tag */}
                {showLabels && (
                  <g>
                    <rect
                      x={obj.px.x}
                      y={obj.px.y - 18}
                      width={
                        obj.label.length * 7 +
                        (obj.confidence * 100).toFixed(0).length * 6 +
                        28
                      }
                      height={18}
                      rx={3}
                      fill={obj.color}
                      opacity={isHovered ? 0.95 : 0.8}
                      style={{ transition: "opacity 0.15s" }}
                    />
                    <text
                      x={obj.px.x + 4}
                      y={obj.px.y - 5}
                      fontSize={11}
                      fontFamily="var(--font-mono), monospace"
                      fontWeight={600}
                      fill="#0a0b0f"
                    >
                      {obj.label} {(obj.confidence * 100).toFixed(0)}%
                    </text>
                  </g>
                )}

                {/* Coordinate display */}
                {showCoords && (
                  <text
                    x={obj.px.x + 4}
                    y={obj.px.y + obj.px.h + 14}
                    fontSize={9}
                    fontFamily="var(--font-mono), monospace"
                    fill={obj.color}
                    opacity={0.7}
                  >
                    [{obj.bbox[0].toFixed(2)}, {obj.bbox[1].toFixed(2)}, {obj.bbox[2].toFixed(2)},{" "}
                    {obj.bbox[3].toFixed(2)}]
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Hover tooltip — positioned relative to container */}
        {hoveredObj && (
          <div
            className="tooltip animate-fade-in"
            style={{
              left: `${((hoveredObj.px.x + hoveredObj.px.w / 2) / SVG_W) * 100}%`,
              bottom: "calc(100% - 4px)",
              transform: "translateX(-50%)",
              animation: "fadeSlideIn 0.15s ease-out both",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 2,
                  background: hoveredObj.color,
                  display: "inline-block",
                }}
              />
              <span style={{ fontWeight: 600 }}>{hoveredObj.label}</span>
              <span style={{ color: "var(--muted-foreground)" }}>
                {(hoveredObj.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.68rem",
                color: "var(--muted-foreground)",
              }}
            >
              bbox: [{hoveredObj.bbox.map((v) => v.toFixed(2)).join(", ")}]
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
          marginTop: "0.75rem",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.72rem",
          color: "var(--muted-foreground)",
        }}
      >
        {SCENE_OBJECTS.map((obj) => (
          <div key={obj.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                border: `2px solid ${obj.color}`,
                display: "inline-block",
              }}
            />
            {obj.label}
          </div>
        ))}
      </div>

      {/* ================================================================ */}
      {/*  Part 2 — IoU Calculator                                         */}
      {/* ================================================================ */}
      {showIoU && (
        <div style={{ marginTop: "1.5rem" }}>
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.78rem",
              color: "#22d3ee",
              fontWeight: 600,
              marginBottom: "0.5rem",
            }}
          >
            IoU Calculator
          </div>
          <p
            style={{
              fontSize: "0.8rem",
              color: "var(--muted-foreground)",
              marginBottom: "0.75rem",
              lineHeight: 1.6,
            }}
          >
            Drag the cyan and orange boxes to change their overlap. IoU (Intersection over Union)
            measures how well a predicted bounding box matches the ground truth.
          </p>

          <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", alignItems: "flex-start" }}>
            {/* IoU SVG canvas */}
            <svg
              ref={iouSvgRef}
              viewBox={`0 0 ${IOU_W} ${IOU_H}`}
              style={{
                width: "100%",
                maxWidth: IOU_W,
                background: "#0d0e14",
                borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.06)",
                display: "block",
                cursor: dragging ? "grabbing" : "default",
                userSelect: "none",
                flexShrink: 0,
              }}
              onMouseMove={handleIoUMouseMove}
              onMouseUp={handleIoUMouseUp}
              onMouseLeave={handleIoUMouseUp}
            >
              {/* Subtle grid */}
              {Array.from({ length: Math.floor(IOU_W / 40) + 1 }).map((_, i) => (
                <line
                  key={`iv${i}`}
                  x1={i * 40}
                  y1={0}
                  x2={i * 40}
                  y2={IOU_H}
                  stroke="rgba(255,255,255,0.04)"
                  strokeWidth={0.5}
                />
              ))}
              {Array.from({ length: Math.floor(IOU_H / 40) + 1 }).map((_, i) => (
                <line
                  key={`ih${i}`}
                  x1={0}
                  y1={i * 40}
                  x2={IOU_W}
                  y2={i * 40}
                  stroke="rgba(255,255,255,0.04)"
                  strokeWidth={0.5}
                />
              ))}

              {/* Intersection (drawn first so it sits behind borders) */}
              {intersection && (
                <rect
                  x={intersection.x}
                  y={intersection.y}
                  width={intersection.w}
                  height={intersection.h}
                  fill="#facc15"
                  opacity={0.35}
                  rx={2}
                />
              )}

              {/* Rect A (cyan / prediction) */}
              <rect
                x={rectA.x}
                y={rectA.y}
                width={rectA.w}
                height={rectA.h}
                fill="#22d3ee"
                fillOpacity={0.12}
                stroke="#22d3ee"
                strokeWidth={2}
                rx={3}
                style={{ cursor: "grab" }}
                onMouseDown={(e) => handleIoUMouseDown("A", e)}
              />
              <text
                x={rectA.x + 6}
                y={rectA.y + 16}
                fontSize={11}
                fontFamily="var(--font-mono), monospace"
                fontWeight={600}
                fill="#22d3ee"
                pointerEvents="none"
              >
                Predicted
              </text>

              {/* Rect B (orange / ground truth) */}
              <rect
                x={rectB.x}
                y={rectB.y}
                width={rectB.w}
                height={rectB.h}
                fill="#f97316"
                fillOpacity={0.12}
                stroke="#f97316"
                strokeWidth={2}
                rx={3}
                style={{ cursor: "grab" }}
                onMouseDown={(e) => handleIoUMouseDown("B", e)}
              />
              <text
                x={rectB.x + 6}
                y={rectB.y + 16}
                fontSize={11}
                fontFamily="var(--font-mono), monospace"
                fontWeight={600}
                fill="#f97316"
                pointerEvents="none"
              >
                Ground Truth
              </text>

              {/* Intersection label */}
              {intersection && intersection.w > 30 && intersection.h > 20 && (
                <text
                  x={intersection.x + intersection.w / 2}
                  y={intersection.y + intersection.h / 2 + 4}
                  fontSize={10}
                  fontFamily="var(--font-mono), monospace"
                  fontWeight={600}
                  fill="#facc15"
                  textAnchor="middle"
                  pointerEvents="none"
                >
                  {"\u2229"}
                </text>
              )}
            </svg>

            {/* IoU formula + result */}
            <div style={{ flex: "1 1 200px", minWidth: 200 }}>
              <div className="code-block" style={{ marginBottom: "0.75rem" }}>
                <div style={{ color: "var(--muted-foreground)", marginBottom: 6 }}>
                  <span style={{ color: "#22d3ee" }}>IoU</span> = Area(
                  <span style={{ color: "#facc15" }}>{"\u2229"}</span>) / Area(
                  <span style={{ color: "#a78bfa" }}>{"\u222a"}</span>)
                </div>
                <div style={{ marginTop: 8, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ color: "var(--muted-foreground)" }}>Area(Predicted)</span>
                    <span style={{ color: "#22d3ee" }}>{(rectA.w * rectA.h).toFixed(0)} px</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ color: "var(--muted-foreground)" }}>Area(Ground Truth)</span>
                    <span style={{ color: "#f97316" }}>{(rectB.w * rectB.h).toFixed(0)} px</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ color: "var(--muted-foreground)" }}>
                      Area(<span style={{ color: "#facc15" }}>{"\u2229"}</span>)
                    </span>
                    <span style={{ color: "#facc15" }}>
                      {intersection ? (intersection.w * intersection.h).toFixed(0) : "0"} px
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--muted-foreground)" }}>
                      Area(<span style={{ color: "#a78bfa" }}>{"\u222a"}</span>)
                    </span>
                    <span style={{ color: "#a78bfa" }}>
                      {(
                        rectA.w * rectA.h +
                        rectB.w * rectB.h -
                        (intersection ? intersection.w * intersection.h : 0)
                      ).toFixed(0)}{" "}
                      px
                    </span>
                  </div>
                </div>
              </div>

              {/* IoU result bar */}
              <div
                style={{
                  background: "rgba(0,0,0,0.4)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "0.75rem 1rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "0.78rem",
                      color: "var(--muted-foreground)",
                    }}
                  >
                    IoU
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono), monospace",
                      fontSize: "1.3rem",
                      fontWeight: 700,
                      color:
                        iouValue >= 0.5
                          ? "#4ade80"
                          : iouValue >= 0.25
                            ? "#facc15"
                            : "#f97316",
                    }}
                  >
                    {iouValue.toFixed(3)}
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    height: 6,
                    background: "rgba(255,255,255,0.06)",
                    borderRadius: 3,
                    overflow: "hidden",
                  }}
                >
                  <div
                    className="confidence-bar"
                    style={{
                      width: `${iouValue * 100}%`,
                      background:
                        iouValue >= 0.5
                          ? "#4ade80"
                          : iouValue >= 0.25
                            ? "#facc15"
                            : "#f97316",
                    }}
                  />
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: "0.68rem",
                    color: "var(--muted-foreground)",
                    marginTop: 6,
                  }}
                >
                  {iouValue >= 0.5
                    ? "Good match (IoU >= 0.5)"
                    : iouValue >= 0.25
                      ? "Partial overlap"
                      : iouValue > 0
                        ? "Poor overlap"
                        : "No overlap"}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
