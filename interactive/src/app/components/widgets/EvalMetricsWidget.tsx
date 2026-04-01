"use client";

import { useState, useCallback, useMemo, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Tab = "iou" | "precision" | "editdist";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Compute Levenshtein edit distance between two strings. */
function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    Array(n + 1).fill(0),
  );
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + cost,
      );
    }
  }
  return dp[m][n];
}

/* ------------------------------------------------------------------ */
/*  Shared inline-style constants                                      */
/* ------------------------------------------------------------------ */

const ACCENT = "#facc15";

const mono = (size: string, color = "#e4e4e7"): React.CSSProperties => ({
  fontFamily: "var(--font-mono), monospace",
  fontSize: size,
  color,
});

const sectionTitle: React.CSSProperties = {
  ...mono("0.7rem", "#a1a1aa"),
  textTransform: "uppercase",
  letterSpacing: "0.1em",
  marginBottom: "1rem",
};

const sliderLabel: React.CSSProperties = {
  ...mono("0.72rem", "#a1a1aa"),
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  flexShrink: 0,
};

const divider: React.CSSProperties = {
  height: 1,
  background:
    "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
  margin: "1.25rem 0",
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function EvalMetricsWidget() {
  const [tab, setTab] = useState<Tab>("iou");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  /* ---- IoU state ---- */
  const [boxAx, setBoxAx] = useState(100);

  const handleBoxAx = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setBoxAx(parseInt(e.target.value, 10)),
    [],
  );

  const iou = useMemo(() => {
    const ax = boxAx;
    const ay = 80;
    const aw = 120;
    const ah = 100;
    const bx = 150;
    const by = 100;
    const bw = 120;
    const bh = 100;

    const areaA = aw * ah;
    const areaB = bw * bh;

    const ix1 = Math.max(ax, bx);
    const iy1 = Math.max(ay, by);
    const ix2 = Math.min(ax + aw, bx + bw);
    const iy2 = Math.min(ay + ah, by + bh);

    const iw = Math.max(0, ix2 - ix1);
    const ih = Math.max(0, iy2 - iy1);
    const intersection = iw * ih;
    const union = areaA + areaB - intersection;
    const iouVal = union > 0 ? intersection / union : 0;

    return {
      areaA,
      areaB,
      intersection,
      union,
      iouVal,
      ix1,
      iy1,
      iw,
      ih,
      ax,
      ay,
      aw,
      ah,
      bx,
      by,
      bw,
      bh,
    };
  }, [boxAx]);

  /* ---- Precision / Recall state ---- */
  const [tp, setTp] = useState(12);
  const [fp, setFp] = useState(3);
  const [fn, setFn] = useState(2);

  const handleTp = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setTp(parseInt(e.target.value, 10)),
    [],
  );
  const handleFp = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setFp(parseInt(e.target.value, 10)),
    [],
  );
  const handleFn = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setFn(parseInt(e.target.value, 10)),
    [],
  );

  const prMetrics = useMemo(() => {
    const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
    const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
    const f1 =
      precision + recall > 0
        ? (2 * precision * recall) / (precision + recall)
        : 0;
    return { precision, recall, f1 };
  }, [tp, fp, fn]);

  /* ---- Edit Distance state ---- */
  const [groundTruth, setGroundTruth] = useState("ORACLE CLOUD");
  const [prediction, setPrediction] = useState("0RACLE CL0UD");

  const handleGt = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => setGroundTruth(e.target.value),
    [],
  );
  const handlePred = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => setPrediction(e.target.value),
    [],
  );

  const editMetrics = useMemo(() => {
    const dist = levenshtein(groundTruth, prediction);
    const maxLen = Math.max(groundTruth.length, prediction.length);
    const norm = maxLen > 0 ? dist / maxLen : 0;
    const similarity = 1 - norm;
    return { dist, norm, similarity };
  }, [groundTruth, prediction]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s6">
      {/* ---- Label ---- */}
      <div className="widget-label">Interactive &middot; Evaluation Metrics</div>

      {/* ---- Tab buttons ---- */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <button
          className={tab === "iou" ? "btn-mono active" : "btn-mono"}
          onClick={() => setTab("iou")}
        >
          IoU Calculator
        </button>
        <button
          className={tab === "precision" ? "btn-mono active" : "btn-mono"}
          onClick={() => setTab("precision")}
        >
          Precision / Recall
        </button>
        <button
          className={tab === "editdist" ? "btn-mono active" : "btn-mono"}
          onClick={() => setTab("editdist")}
        >
          Edit Distance
        </button>
      </div>

      {/* ============================================================ */}
      {/*  TAB 1 — IoU Calculator                                      */}
      {/* ============================================================ */}
      {tab === "iou" && (
        <div>
          {/* SVG canvas */}
          {mounted && (
            <div
              style={{
                background: "rgba(0,0,0,0.35)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 10,
                padding: "1rem",
                marginBottom: "1.25rem",
                overflow: "hidden",
              }}
            >
              <svg
                viewBox="0 0 400 300"
                width="100%"
                style={{ display: "block", maxHeight: 260 }}
                aria-label="IoU visualization"
              >
                {/* Box A (yellow) */}
                <rect
                  x={iou.ax}
                  y={iou.ay}
                  width={iou.aw}
                  height={iou.ah}
                  fill="rgba(250,204,21,0.18)"
                  stroke={ACCENT}
                  strokeWidth={2}
                />
                {/* Box B (cyan) */}
                <rect
                  x={iou.bx}
                  y={iou.by}
                  width={iou.bw}
                  height={iou.bh}
                  fill="rgba(34,211,238,0.18)"
                  stroke="#22d3ee"
                  strokeWidth={2}
                />
                {/* Intersection (green) */}
                {iou.iw > 0 && iou.ih > 0 && (
                  <rect
                    x={iou.ix1}
                    y={iou.iy1}
                    width={iou.iw}
                    height={iou.ih}
                    fill="rgba(74,222,128,0.35)"
                    stroke="#4ade80"
                    strokeWidth={1.5}
                    strokeDasharray="4 2"
                  />
                )}
                {/* Labels */}
                <text
                  x={iou.ax + iou.aw / 2}
                  y={iou.ay - 8}
                  textAnchor="middle"
                  fill={ACCENT}
                  fontSize="13"
                  fontFamily="var(--font-mono), monospace"
                >
                  A
                </text>
                <text
                  x={iou.bx + iou.bw / 2}
                  y={iou.by - 8}
                  textAnchor="middle"
                  fill="#22d3ee"
                  fontSize="13"
                  fontFamily="var(--font-mono), monospace"
                >
                  B
                </text>
                {iou.iw > 0 && iou.ih > 0 && (
                  <text
                    x={iou.ix1 + iou.iw / 2}
                    y={iou.iy1 + iou.ih / 2 + 4}
                    textAnchor="middle"
                    fill="#4ade80"
                    fontSize="11"
                    fontFamily="var(--font-mono), monospace"
                  >
                    {iou.intersection}
                  </text>
                )}
              </svg>
            </div>
          )}

          {/* Slider */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              marginBottom: "1.25rem",
              flexWrap: "wrap",
            }}
          >
            <span style={sliderLabel}>Box A X</span>
            <input
              type="range"
              min={50}
              max={200}
              step={1}
              value={boxAx}
              onChange={handleBoxAx}
              aria-label="Box A horizontal offset"
              style={{ flex: 1, minWidth: 120 }}
            />
            <span style={{ ...mono("0.85rem", ACCENT), fontWeight: 600, minWidth: "2.5rem", textAlign: "right" as const }}>
              {boxAx}
            </span>
          </div>

          {/* Computed values */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.4rem",
              ...mono("0.78rem"),
            }}
          >
            <div>
              <span style={{ color: "#a1a1aa" }}>Area A: </span>
              <span style={{ color: ACCENT }}>{iou.aw}&times;{iou.ah} = {iou.areaA}</span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>Area B: </span>
              <span style={{ color: "#22d3ee" }}>{iou.bw}&times;{iou.bh} = {iou.areaB}</span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>Intersection: </span>
              <span style={{ color: "#4ade80" }}>{iou.intersection}</span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>Union: </span>
              <span style={{ color: "#e4e4e7" }}>
                {iou.areaA} + {iou.areaB} &minus; {iou.intersection} = {iou.union}
              </span>
            </div>
            <div style={divider} />
            <div style={{ fontSize: "0.9rem" }}>
              <span style={{ color: "#a1a1aa" }}>IoU = </span>
              <span style={{ color: ACCENT, fontWeight: 700 }}>
                {iou.iouVal.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/*  TAB 2 — Precision / Recall                                   */}
      {/* ============================================================ */}
      {tab === "precision" && (
        <div>
          {/* Confusion matrix */}
          <div style={sectionTitle}>Confusion Matrix</div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "0.5rem",
              marginBottom: "1.5rem",
              maxWidth: 280,
            }}
          >
            {/* TP */}
            <div
              style={{
                background: "rgba(74,222,128,0.12)",
                border: "1px solid rgba(74,222,128,0.3)",
                borderRadius: 8,
                padding: "0.75rem",
                textAlign: "center",
              }}
            >
              <div style={{ ...mono("0.65rem", "#a1a1aa"), marginBottom: "0.25rem" }}>
                True Positive
              </div>
              <div style={{ ...mono("1.2rem", "#4ade80"), fontWeight: 700 }}>
                {tp}
              </div>
            </div>
            {/* FP */}
            <div
              style={{
                background: "rgba(248,113,113,0.12)",
                border: "1px solid rgba(248,113,113,0.3)",
                borderRadius: 8,
                padding: "0.75rem",
                textAlign: "center",
              }}
            >
              <div style={{ ...mono("0.65rem", "#a1a1aa"), marginBottom: "0.25rem" }}>
                False Positive
              </div>
              <div style={{ ...mono("1.2rem", "#f87171"), fontWeight: 700 }}>
                {fp}
              </div>
            </div>
            {/* FN */}
            <div
              style={{
                background: "rgba(251,191,36,0.12)",
                border: "1px solid rgba(251,191,36,0.3)",
                borderRadius: 8,
                padding: "0.75rem",
                textAlign: "center",
              }}
            >
              <div style={{ ...mono("0.65rem", "#a1a1aa"), marginBottom: "0.25rem" }}>
                False Negative
              </div>
              <div style={{ ...mono("1.2rem", "#fbbf24"), fontWeight: 700 }}>
                {fn}
              </div>
            </div>
            {/* TN */}
            <div
              style={{
                background: "rgba(161,161,170,0.08)",
                border: "1px solid rgba(161,161,170,0.2)",
                borderRadius: 8,
                padding: "0.75rem",
                textAlign: "center",
              }}
            >
              <div style={{ ...mono("0.65rem", "#a1a1aa"), marginBottom: "0.25rem" }}>
                True Negative
              </div>
              <div style={{ ...mono("1.2rem", "#a1a1aa"), fontWeight: 700 }}>
                &mdash;
              </div>
            </div>
          </div>

          {/* Sliders */}
          {([
            { label: "TP", value: tp, handler: handleTp, color: "#4ade80" },
            { label: "FP", value: fp, handler: handleFp, color: "#f87171" },
            { label: "FN", value: fn, handler: handleFn, color: "#fbbf24" },
          ] as const).map((s) => (
            <div
              key={s.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                marginBottom: "0.6rem",
                flexWrap: "wrap",
              }}
            >
              <span style={{ ...sliderLabel, width: 24 }}>{s.label}</span>
              <input
                type="range"
                min={0}
                max={20}
                step={1}
                value={s.value}
                onChange={s.handler}
                aria-label={s.label}
                style={{ flex: 1, minWidth: 120 }}
              />
              <span
                style={{
                  ...mono("0.85rem", s.color),
                  fontWeight: 600,
                  minWidth: "1.8rem",
                  textAlign: "right" as const,
                }}
              >
                {s.value}
              </span>
            </div>
          ))}

          <div style={divider} />

          {/* Metrics readout */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.4rem",
              marginBottom: "1.25rem",
              ...mono("0.78rem"),
            }}
          >
            <div>
              <span style={{ color: "#a1a1aa" }}>Precision = TP / (TP + FP) = </span>
              <span style={{ color: ACCENT, fontWeight: 700 }}>
                {prMetrics.precision.toFixed(2)}
              </span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>Recall = TP / (TP + FN) = </span>
              <span style={{ color: ACCENT, fontWeight: 700 }}>
                {prMetrics.recall.toFixed(2)}
              </span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>F1 = 2(P&times;R)/(P+R) = </span>
              <span style={{ color: ACCENT, fontWeight: 700 }}>
                {prMetrics.f1.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Bar charts */}
          {mounted && (
            <div
              style={{
                display: "flex",
                gap: "1.5rem",
                alignItems: "flex-end",
                height: 100,
              }}
            >
              {([
                { label: "P", value: prMetrics.precision, color: "#4ade80" },
                { label: "R", value: prMetrics.recall, color: "#22d3ee" },
                { label: "F1", value: prMetrics.f1, color: ACCENT },
              ] as const).map((bar) => (
                <div
                  key={bar.label}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "0.3rem",
                    flex: 1,
                  }}
                >
                  <span style={mono("0.72rem", bar.color)}>
                    {bar.value.toFixed(2)}
                  </span>
                  <div
                    style={{
                      width: "100%",
                      maxWidth: 40,
                      background: "rgba(255,255,255,0.06)",
                      borderRadius: 4,
                      height: 60,
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        bottom: 0,
                        left: 0,
                        right: 0,
                        height: `${bar.value * 100}%`,
                        background: bar.color,
                        borderRadius: 4,
                        opacity: 0.7,
                        transition: "height 0.3s ease",
                      }}
                    />
                  </div>
                  <span style={mono("0.68rem", "#a1a1aa")}>{bar.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/*  TAB 3 — Edit Distance                                        */}
      {/* ============================================================ */}
      {tab === "editdist" && (
        <div>
          {/* Text inputs */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.25rem" }}>
            <div>
              <label style={{ ...mono("0.68rem", "#a1a1aa"), display: "block", marginBottom: "0.35rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Ground Truth
              </label>
              <input
                type="text"
                value={groundTruth}
                onChange={handleGt}
                spellCheck={false}
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.35)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 6,
                  padding: "0.5rem 0.75rem",
                  color: "#e4e4e7",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
              />
            </div>
            <div>
              <label style={{ ...mono("0.68rem", "#a1a1aa"), display: "block", marginBottom: "0.35rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Prediction
              </label>
              <input
                type="text"
                value={prediction}
                onChange={handlePred}
                spellCheck={false}
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.35)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 6,
                  padding: "0.5rem 0.75rem",
                  color: "#e4e4e7",
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
              />
            </div>
          </div>

          {/* Character comparison grid */}
          <div style={sectionTitle}>Character Comparison</div>
          <div
            style={{
              display: "flex",
              gap: "2px",
              flexWrap: "wrap",
              marginBottom: "1.25rem",
            }}
          >
            {Array.from({ length: Math.max(groundTruth.length, prediction.length) }).map((_, i) => {
              const gChar = i < groundTruth.length ? groundTruth[i] : "";
              const pChar = i < prediction.length ? prediction[i] : "";
              const match = gChar !== "" && pChar !== "" && gChar === pChar;
              const bgColor = match
                ? "rgba(74,222,128,0.18)"
                : "rgba(248,113,113,0.18)";
              const borderColor = match
                ? "rgba(74,222,128,0.35)"
                : "rgba(248,113,113,0.35)";

              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "2px",
                    background: bgColor,
                    border: `1px solid ${borderColor}`,
                    borderRadius: 4,
                    padding: "0.35rem 0.4rem",
                    minWidth: 28,
                  }}
                >
                  <span
                    style={{
                      ...mono("0.75rem", match ? "#4ade80" : "#f87171"),
                      fontWeight: 600,
                    }}
                  >
                    {gChar || "\u00A0"}
                  </span>
                  <div
                    style={{
                      width: "100%",
                      height: 1,
                      background: "rgba(255,255,255,0.1)",
                    }}
                  />
                  <span
                    style={{
                      ...mono("0.75rem", match ? "#4ade80" : "#f87171"),
                      fontWeight: 600,
                    }}
                  >
                    {pChar || "\u00A0"}
                  </span>
                </div>
              );
            })}
          </div>

          <div style={divider} />

          {/* Metrics readout */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.4rem",
              ...mono("0.78rem"),
            }}
          >
            <div>
              <span style={{ color: "#a1a1aa" }}>Edit Distance: </span>
              <span style={{ color: "#f87171", fontWeight: 700 }}>
                {editMetrics.dist}
              </span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>Normalized: </span>
              <span style={{ color: "#e4e4e7" }}>
                {editMetrics.dist} / {Math.max(groundTruth.length, prediction.length)} ={" "}
                <span style={{ fontWeight: 600 }}>{editMetrics.norm.toFixed(2)}</span>
              </span>
            </div>
            <div>
              <span style={{ color: "#a1a1aa" }}>Similarity: </span>
              <span style={{ color: "#4ade80", fontWeight: 700 }}>
                {editMetrics.similarity.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
