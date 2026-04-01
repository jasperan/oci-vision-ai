"use client";

import { useState, useCallback, useMemo, useEffect, useRef } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface LineItem {
  item: string;
  qty: number;
  amount: string;
}

interface FieldInfo {
  key: string;
  label: string;
  value: string;
  confidence: number;
  bbox: { x: number; y: number; w: number; h: number };
}

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

const LINE_ITEMS: LineItem[] = [
  { item: "Cloud Credit", qty: 100, amount: "$2,500" },
  { item: "Support Plan", qty: 1, amount: "$499" },
  { item: "Training", qty: 2, amount: "$1,200" },
];

const FIELDS: FieldInfo[] = [
  {
    key: "invoice_number",
    label: "Invoice #",
    value: "INV-1001",
    confidence: 0.99,
    bbox: { x: 68, y: 4, w: 28, h: 7 },
  },
  {
    key: "date",
    label: "Date",
    value: "2024-03-15",
    confidence: 0.97,
    bbox: { x: 5, y: 13, w: 40, h: 7 },
  },
  {
    key: "vendor",
    label: "Vendor",
    value: "Oracle Corp",
    confidence: 0.96,
    bbox: { x: 5, y: 21, w: 45, h: 7 },
  },
  {
    key: "subtotal",
    label: "Subtotal",
    value: "$4,199",
    confidence: 0.98,
    bbox: { x: 5, y: 72, w: 50, h: 7 },
  },
  {
    key: "tax",
    label: "Tax (8%)",
    value: "$335.92",
    confidence: 0.95,
    bbox: { x: 5, y: 80, w: 50, h: 7 },
  },
  {
    key: "total",
    label: "Total",
    value: "$4,534.92",
    confidence: 0.99,
    bbox: { x: 5, y: 88, w: 50, h: 7 },
  },
];

const STAGES = [
  { id: 0, label: "Raw Document" },
  { id: 1, label: "Field Detection" },
  { id: 2, label: "Value Extraction" },
  { id: 3, label: "Structured Output" },
] as const;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const ACCENT = "#f472b6";
const ACCENT_DIM = "rgba(244,114,182,0.25)";
const ACCENT_GLOW = "rgba(244,114,182,0.15)";

const mono: React.CSSProperties = {
  fontFamily: "var(--font-mono), monospace",
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function InvoiceDocument({
  stage,
  selectedField,
  onFieldClick,
}: {
  stage: number;
  selectedField: string | null;
  onFieldClick: (key: string) => void;
}) {
  const showHighlights = stage >= 1;
  const showTable = stage >= 1;

  const fieldStyle = useCallback(
    (field: FieldInfo): React.CSSProperties => {
      if (!showHighlights) return {};
      const isSelected = selectedField === field.key;
      return {
        border: `1.5px dashed ${isSelected ? ACCENT : "rgba(244,114,182,0.5)"}`,
        borderRadius: 3,
        padding: "1px 4px",
        cursor: "pointer",
        background: isSelected ? ACCENT_GLOW : "transparent",
        transition: "all 0.2s ease",
        display: "inline-block",
      };
    },
    [showHighlights, selectedField],
  );

  const handleClick = useCallback(
    (key: string) => {
      if (showHighlights) onFieldClick(key);
    },
    [showHighlights, onFieldClick],
  );

  return (
    <div
      style={{
        background: "rgba(0,0,0,0.45)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 10,
        padding: "1.25rem 1.5rem",
        ...mono,
        fontSize: "0.78rem",
        lineHeight: 1.8,
        color: "#e4e4e7",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "0.5rem",
        }}
      >
        <span
          style={{
            fontSize: "1.1rem",
            fontWeight: 700,
            color: "#e4e4e7",
            letterSpacing: "0.08em",
          }}
        >
          INVOICE
        </span>
        <span
          style={fieldStyle(FIELDS[0])}
          onClick={() => handleClick("invoice_number")}
          role={showHighlights ? "button" : undefined}
          tabIndex={showHighlights ? 0 : undefined}
        >
          #INV-1001
        </span>
      </div>

      {/* Date & Vendor */}
      <div style={{ marginBottom: "0.15rem" }}>
        <span style={{ color: "#a1a1aa" }}>Date: </span>
        <span
          style={fieldStyle(FIELDS[1])}
          onClick={() => handleClick("date")}
          role={showHighlights ? "button" : undefined}
          tabIndex={showHighlights ? 0 : undefined}
        >
          2024-03-15
        </span>
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ color: "#a1a1aa" }}>Vendor: </span>
        <span
          style={fieldStyle(FIELDS[2])}
          onClick={() => handleClick("vendor")}
          role={showHighlights ? "button" : undefined}
          tabIndex={showHighlights ? 0 : undefined}
        >
          Oracle Corp
        </span>
      </div>

      {/* Line items table */}
      <div
        style={{
          border: showTable
            ? `1px solid rgba(244,114,182,0.25)`
            : "1px solid rgba(255,255,255,0.06)",
          borderRadius: 6,
          overflow: "hidden",
          marginBottom: "1rem",
          transition: "border-color 0.3s ease",
        }}
      >
        {/* Table header */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 60px 80px",
            gap: 0,
            background: showTable
              ? "rgba(244,114,182,0.06)"
              : "rgba(255,255,255,0.03)",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            padding: "0.4rem 0.75rem",
            fontSize: "0.7rem",
            color: "#a1a1aa",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            fontWeight: 600,
            transition: "background 0.3s ease",
          }}
        >
          <span>Item</span>
          <span style={{ textAlign: "right" }}>Qty</span>
          <span style={{ textAlign: "right" }}>Amount</span>
        </div>

        {/* Table rows */}
        {LINE_ITEMS.map((item, i) => (
          <div
            key={item.item}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 60px 80px",
              gap: 0,
              padding: "0.4rem 0.75rem",
              borderBottom:
                i < LINE_ITEMS.length - 1
                  ? "1px solid rgba(255,255,255,0.04)"
                  : "none",
              background:
                showTable && i % 2 === 0
                  ? "rgba(244,114,182,0.02)"
                  : "transparent",
              transition: "background 0.3s ease",
            }}
          >
            <span>{item.item}</span>
            <span style={{ textAlign: "right", color: "#a1a1aa" }}>
              {item.qty}
            </span>
            <span style={{ textAlign: "right" }}>{item.amount}</span>
          </div>
        ))}
      </div>

      {/* Totals */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.15rem",
          paddingLeft: "0.25rem",
        }}
      >
        <div>
          <span style={{ color: "#a1a1aa" }}>Subtotal: </span>
          <span
            style={fieldStyle(FIELDS[3])}
            onClick={() => handleClick("subtotal")}
            role={showHighlights ? "button" : undefined}
            tabIndex={showHighlights ? 0 : undefined}
          >
            $4,199
          </span>
        </div>
        <div>
          <span style={{ color: "#a1a1aa" }}>Tax (8%): </span>
          <span
            style={fieldStyle(FIELDS[4])}
            onClick={() => handleClick("tax")}
            role={showHighlights ? "button" : undefined}
            tabIndex={showHighlights ? 0 : undefined}
          >
            $335.92
          </span>
        </div>
        <div style={{ fontWeight: 700 }}>
          <span style={{ color: "#a1a1aa" }}>Total: </span>
          <span
            style={fieldStyle(FIELDS[5])}
            onClick={() => handleClick("total")}
            role={showHighlights ? "button" : undefined}
            tabIndex={showHighlights ? 0 : undefined}
          >
            $4,534.92
          </span>
        </div>
      </div>
    </div>
  );
}

function FieldDetailPanel({ field }: { field: FieldInfo }) {
  const pct = Math.round(field.confidence * 100);
  return (
    <div
      className="animate-slide-in"
      style={{
        background: "rgba(244,114,182,0.06)",
        border: `1px solid rgba(244,114,182,0.2)`,
        borderRadius: 8,
        padding: "0.85rem 1rem",
        ...mono,
        fontSize: "0.75rem",
      }}
    >
      <div
        style={{
          fontSize: "0.68rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: ACCENT,
          marginBottom: "0.6rem",
          fontWeight: 600,
        }}
      >
        Field Details
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "0.25rem 0.75rem" }}>
        <span style={{ color: "#a1a1aa" }}>Field</span>
        <span style={{ color: "#e4e4e7" }}>{field.label}</span>
        <span style={{ color: "#a1a1aa" }}>Value</span>
        <span style={{ color: "#e4e4e7", fontWeight: 600 }}>{field.value}</span>
        <span style={{ color: "#a1a1aa" }}>Confidence</span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ color: ACCENT, fontWeight: 600 }}>{pct}%</span>
          <span
            style={{
              flex: 1,
              maxWidth: 100,
              height: 4,
              borderRadius: 2,
              background: "rgba(255,255,255,0.06)",
              overflow: "hidden",
            }}
          >
            <span
              style={{
                display: "block",
                width: `${pct}%`,
                height: "100%",
                borderRadius: 2,
                background: `linear-gradient(90deg, ${ACCENT}, #f9a8d4)`,
              }}
            />
          </span>
        </span>
        <span style={{ color: "#a1a1aa" }}>Bounding Box</span>
        <span style={{ color: "#a1a1aa", fontSize: "0.7rem" }}>
          [{field.bbox.x}, {field.bbox.y}, {field.bbox.w}, {field.bbox.h}]
        </span>
      </div>
    </div>
  );
}

function ExtractedPairsPanel() {
  return (
    <div
      className="animate-fade-in-up"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.4rem",
      }}
    >
      <div
        style={{
          ...mono,
          fontSize: "0.68rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: ACCENT,
          marginBottom: "0.25rem",
          fontWeight: 600,
        }}
      >
        Extracted Key-Value Pairs
      </div>
      {FIELDS.map((f) => {
        const pct = Math.round(f.confidence * 100);
        return (
          <div
            key={f.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              ...mono,
              fontSize: "0.75rem",
            }}
          >
            <span
              style={{
                color: "#a1a1aa",
                width: 80,
                textAlign: "right",
                flexShrink: 0,
              }}
            >
              {f.label}
            </span>
            <span
              style={{
                color: "#e4e4e7",
                fontWeight: 600,
                flex: 1,
              }}
            >
              {f.value}
            </span>
            <span
              style={{
                width: 60,
                height: 4,
                borderRadius: 2,
                background: "rgba(255,255,255,0.06)",
                overflow: "hidden",
                flexShrink: 0,
              }}
            >
              <span
                className="confidence-bar"
                style={{
                  display: "block",
                  width: `${pct}%`,
                  height: "100%",
                  borderRadius: 2,
                  background: `linear-gradient(90deg, ${ACCENT}, #f9a8d4)`,
                }}
              />
            </span>
            <span
              style={{
                color: ACCENT,
                fontSize: "0.7rem",
                fontWeight: 600,
                width: 32,
                textAlign: "right",
                flexShrink: 0,
              }}
            >
              {pct}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

function StructuredJsonOutput() {
  return (
    <div className="animate-fade-in-up">
      <div
        style={{
          ...mono,
          fontSize: "0.68rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: ACCENT,
          marginBottom: "0.6rem",
          fontWeight: 600,
        }}
      >
        Structured Output
      </div>
      <div className="code-block" style={{ fontSize: "0.74rem" }}>
        <span className="json-bracket">{"{"}</span>
        <br />
        {"  "}
        <span className="json-key">&quot;invoice_number&quot;</span>
        {": "}
        <span className="json-string">&quot;INV-1001&quot;</span>,
        <br />
        {"  "}
        <span className="json-key">&quot;date&quot;</span>
        {": "}
        <span className="json-string">&quot;2024-03-15&quot;</span>,
        <br />
        {"  "}
        <span className="json-key">&quot;vendor&quot;</span>
        {": "}
        <span className="json-string">&quot;Oracle Corp&quot;</span>,
        <br />
        {"  "}
        <span className="json-key">&quot;subtotal&quot;</span>
        {": "}
        <span className="json-number">4199.00</span>,
        <br />
        {"  "}
        <span className="json-key">&quot;tax&quot;</span>
        {": "}
        <span className="json-number">335.92</span>,
        <br />
        {"  "}
        <span className="json-key">&quot;total&quot;</span>
        {": "}
        <span className="json-number">4534.92</span>,
        <br />
        {"  "}
        <span className="json-key">&quot;line_items&quot;</span>
        {": "}
        <span className="json-bracket">[</span>
        <br />
        {"    "}
        <span className="json-bracket">{"{"}</span>
        <br />
        {"      "}
        <span className="json-key">&quot;item&quot;</span>
        {": "}
        <span className="json-string">&quot;Cloud Credit&quot;</span>,
        <br />
        {"      "}
        <span className="json-key">&quot;qty&quot;</span>
        {": "}
        <span className="json-number">100</span>,
        <br />
        {"      "}
        <span className="json-key">&quot;amount&quot;</span>
        {": "}
        <span className="json-number">2500.00</span>
        <br />
        {"    "}
        <span className="json-bracket">{"}"}</span>,
        <br />
        {"    "}
        <span className="json-bracket">{"{"}</span>
        <br />
        {"      "}
        <span className="json-key">&quot;item&quot;</span>
        {": "}
        <span className="json-string">&quot;Support Plan&quot;</span>,
        <br />
        {"      "}
        <span className="json-key">&quot;qty&quot;</span>
        {": "}
        <span className="json-number">1</span>,
        <br />
        {"      "}
        <span className="json-key">&quot;amount&quot;</span>
        {": "}
        <span className="json-number">499.00</span>
        <br />
        {"    "}
        <span className="json-bracket">{"}"}</span>,
        <br />
        {"    "}
        <span className="json-bracket">{"{"}</span>
        <br />
        {"      "}
        <span className="json-key">&quot;item&quot;</span>
        {": "}
        <span className="json-string">&quot;Training&quot;</span>,
        <br />
        {"      "}
        <span className="json-key">&quot;qty&quot;</span>
        {": "}
        <span className="json-number">2</span>,
        <br />
        {"      "}
        <span className="json-key">&quot;amount&quot;</span>
        {": "}
        <span className="json-number">1200.00</span>
        <br />
        {"    "}
        <span className="json-bracket">{"}"}</span>
        <br />
        {"  "}
        <span className="json-bracket">]</span>
        <br />
        <span className="json-bracket">{"}"}</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main widget                                                        */
/* ------------------------------------------------------------------ */

export default function DocumentAiWidget() {
  const [stage, setStage] = useState(0);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const autoPlayRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Auto-play logic */
  useEffect(() => {
    if (!autoPlaying) {
      if (autoPlayRef.current) clearTimeout(autoPlayRef.current);
      return;
    }
    if (stage >= 3) {
      setAutoPlaying(false);
      return;
    }
    autoPlayRef.current = setTimeout(() => {
      setStage((s) => s + 1);
    }, 1800);
    return () => {
      if (autoPlayRef.current) clearTimeout(autoPlayRef.current);
    };
  }, [autoPlaying, stage]);

  const handleStep = useCallback(() => {
    setAutoPlaying(false);
    setStage((s) => Math.min(s + 1, 3));
    setSelectedField(null);
  }, []);

  const handleReset = useCallback(() => {
    setAutoPlaying(false);
    setStage(0);
    setSelectedField(null);
  }, []);

  const handleAutoPlay = useCallback(() => {
    if (autoPlaying) {
      setAutoPlaying(false);
    } else {
      if (stage >= 3) setStage(0);
      setAutoPlaying(true);
    }
  }, [autoPlaying, stage]);

  const handleFieldClick = useCallback(
    (key: string) => {
      if (stage < 1) return;
      setSelectedField((prev) => (prev === key ? null : key));
    },
    [stage],
  );

  const selectedFieldData = useMemo(
    () => FIELDS.find((f) => f.key === selectedField) ?? null,
    [selectedField],
  );

  return (
    <div className="widget-container s5">
      {/* ---- Label ---- */}
      <div className="widget-label">Interactive &middot; Document AI</div>

      {/* ---- Stage indicator ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.35rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        {STAGES.map((s, i) => (
          <div
            key={s.id}
            style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}
          >
            <button
              onClick={() => {
                setAutoPlaying(false);
                setStage(s.id);
                setSelectedField(null);
              }}
              style={{
                ...mono,
                fontSize: "0.68rem",
                padding: "0.25rem 0.6rem",
                borderRadius: 4,
                border:
                  stage === s.id
                    ? `1px solid ${ACCENT}`
                    : "1px solid rgba(255,255,255,0.06)",
                background:
                  stage === s.id ? ACCENT_GLOW : "rgba(255,255,255,0.02)",
                color: stage === s.id ? ACCENT : stage > s.id ? "#e4e4e7" : "#a1a1aa",
                cursor: "pointer",
                transition: "all 0.2s ease",
                fontWeight: stage === s.id ? 600 : 400,
                whiteSpace: "nowrap",
              }}
            >
              {s.label}
            </button>
            {i < STAGES.length - 1 && (
              <span
                style={{
                  color:
                    stage > i
                      ? "rgba(244,114,182,0.6)"
                      : "rgba(255,255,255,0.15)",
                  fontSize: "0.7rem",
                  transition: "color 0.3s ease",
                }}
                aria-hidden="true"
              >
                &rarr;
              </span>
            )}
          </div>
        ))}
      </div>

      {/* ---- Invoice document ---- */}
      <InvoiceDocument
        stage={stage}
        selectedField={selectedField}
        onFieldClick={handleFieldClick}
      />

      {/* ---- Field detail panel ---- */}
      {stage >= 1 && selectedFieldData && (
        <div style={{ marginTop: "1rem" }}>
          <FieldDetailPanel field={selectedFieldData} />
        </div>
      )}

      {/* ---- Extracted key-value pairs ---- */}
      {stage >= 2 && (
        <div style={{ marginTop: "1.25rem" }}>
          <ExtractedPairsPanel />
        </div>
      )}

      {/* ---- Divider ---- */}
      <div
        style={{
          height: 1,
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
          margin: "1.5rem 0",
        }}
      />

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
          className={`btn-mono${stage < 3 ? " active" : ""}`}
          onClick={handleStep}
          disabled={stage >= 3}
          style={{ opacity: stage >= 3 ? 0.4 : 1 }}
        >
          Step
        </button>
        <button className="btn-mono" onClick={handleReset}>
          Reset
        </button>
        <button
          className={`btn-mono${autoPlaying ? " active" : ""}`}
          onClick={handleAutoPlay}
        >
          {autoPlaying ? "Pause" : "Auto-Play"}
        </button>
        <span
          style={{
            ...mono,
            fontSize: "0.7rem",
            color: "#a1a1aa",
            marginLeft: "auto",
          }}
        >
          Stage {stage + 1} / {STAGES.length}
        </span>
      </div>

      {/* ---- Structured JSON output ---- */}
      {stage >= 3 && <StructuredJsonOutput />}
    </div>
  );
}
