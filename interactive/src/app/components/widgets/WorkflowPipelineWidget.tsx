"use client";

import { useState, useCallback, useRef, useEffect } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type StageStatus = "pending" | "active" | "completed";

interface PipelineStage {
  name: string;
  description: string;
  features: string[];
  codeSnippet: string;
}

interface Workflow {
  id: string;
  label: string;
  subtitle: string;
  stages: PipelineStage[];
  cliCommand: string;
}

/* ------------------------------------------------------------------ */
/*  Static data                                                        */
/* ------------------------------------------------------------------ */

const WORKFLOWS: Workflow[] = [
  {
    id: "receipt",
    label: "Receipt Intake",
    subtitle: "Document AI",
    stages: [
      {
        name: "Upload",
        description: "Receipt image is submitted to the pipeline for processing.",
        features: ["Image Input"],
        codeSnippet: `const input = await readFile("invoice.png");
await client.upload(input, { type: "receipt" });`,
      },
      {
        name: "Document AI",
        description: "OCI Document AI detects document structure — tables, headers, key-value pairs.",
        features: ["Document AI"],
        codeSnippet: `const doc = await vision.analyzeDocument({
  image: input,
  features: ["KEY_VALUE_DETECTION", "TABLE_DETECTION"],
});`,
      },
      {
        name: "Field Extraction",
        description: "Structured fields like vendor, total, date, and line items are extracted.",
        features: ["Document AI", "OCR"],
        codeSnippet: `const fields = doc.pages.flatMap(p => p.keyValuePairs);
const total = fields.find(f => f.key === "Total");`,
      },
      {
        name: "Validation",
        description: "Extracted values are validated against business rules and expected formats.",
        features: ["Custom Logic"],
        codeSnippet: `const valid = validate(fields, {
  required: ["vendor", "total", "date"],
  totalRange: [0, 100000],
});`,
      },
      {
        name: "Structured Output",
        description: "Clean JSON output ready for downstream systems — ERP, accounting, or storage.",
        features: ["JSON Output"],
        codeSnippet: `return {
  vendor: fields.vendor,
  total: fields.total,
  lineItems: fields.items,
  confidence: doc.confidence,
};`,
      },
    ],
    cliCommand: "oci-vision workflow receipt invoice.png --demo",
  },
  {
    id: "shelf",
    label: "Shelf Audit",
    subtitle: "Object Detection",
    stages: [
      {
        name: "Capture",
        description: "Shelf photograph is captured from store camera or mobile device.",
        features: ["Image Input"],
        codeSnippet: `const frame = await camera.capture({
  resolution: "1920x1080",
  format: "jpeg",
});`,
      },
      {
        name: "Object Detection",
        description: "OCI Vision detects individual products on the shelf with bounding boxes.",
        features: ["Object Detection"],
        codeSnippet: `const detections = await vision.detectObjects({
  image: frame,
  model: "retail-shelf-v2",
  maxResults: 200,
});`,
      },
      {
        name: "Count & Classify",
        description: "Detected objects are counted per category — brand, SKU, or product type.",
        features: ["Object Detection", "Classification"],
        codeSnippet: `const counts = detections.objects.reduce(
  (acc, obj) => {
    acc[obj.label] = (acc[obj.label] || 0) + 1;
    return acc;
  }, {}
);`,
      },
      {
        name: "Aggregation",
        description: "Per-shelf counts are aggregated across zones and compared to planogram.",
        features: ["Custom Logic"],
        codeSnippet: `const report = aggregate(counts, {
  planogram: await loadPlanogram(storeId),
  tolerance: 0.1,
});`,
      },
      {
        name: "Summary Report",
        description: "Final audit report with stock levels, gaps, and restocking recommendations.",
        features: ["JSON Output"],
        codeSnippet: `return {
  totalProducts: report.total,
  outOfStock: report.gaps,
  compliance: report.score,
  recommendations: report.actions,
};`,
      },
    ],
    cliCommand: "oci-vision workflow shelf shelf_photo.jpg --demo",
  },
  {
    id: "inspection",
    label: "Inspection",
    subtitle: "Classification + Detection + OCR",
    stages: [
      {
        name: "Photograph",
        description: "Part or assembly photograph is taken for quality inspection.",
        features: ["Image Input"],
        codeSnippet: `const photo = await inspector.capture({
  station: "QA-Line-3",
  partId: partSerial,
});`,
      },
      {
        name: "Classification",
        description: "Image is classified as normal, defective, or requires further review.",
        features: ["Classification"],
        codeSnippet: `const cls = await vision.classifyImage({
  image: photo,
  model: "defect-classifier-v3",
  topN: 3,
});`,
      },
      {
        name: "Detection",
        description: "Specific defect regions are detected and localized with bounding boxes.",
        features: ["Object Detection"],
        codeSnippet: `const defects = await vision.detectObjects({
  image: photo,
  model: "defect-detector-v3",
  threshold: 0.6,
});`,
      },
      {
        name: "OCR",
        description: "Serial numbers and labels on the part are read for traceability.",
        features: ["OCR"],
        codeSnippet: `const text = await vision.extractText({
  image: photo,
  languages: ["en"],
});
const serial = text.lines.find(l => l.match(/SN-/));`,
      },
      {
        name: "Combined Report",
        description: "All analyses merge into a unified inspection report with evidence.",
        features: ["Classification", "Object Detection", "OCR"],
        codeSnippet: `const report = mergeResults({
  classification: cls,
  defects: defects.objects,
  serialNumber: serial,
});`,
      },
      {
        name: "Pass/Fail",
        description: "Final verdict is issued based on configurable quality thresholds.",
        features: ["Custom Logic"],
        codeSnippet: `const verdict = report.defects.length === 0
  && cls.topLabel === "normal"
  ? "PASS" : "FAIL";
return { verdict, report };`,
      },
    ],
    cliCommand: "oci-vision workflow inspection part.jpg --demo",
  },
  {
    id: "archive",
    label: "Archive Search",
    subtitle: "OCR + Document AI",
    stages: [
      {
        name: "Upload Batch",
        description: "A batch of scanned documents is uploaded for processing.",
        features: ["Image Input"],
        codeSnippet: `const batch = await glob("./scans/*.pdf");
await client.uploadBatch(batch, {
  parallel: 4,
});`,
      },
      {
        name: "OCR All",
        description: "Every page in the batch is run through OCR to extract raw text.",
        features: ["OCR"],
        codeSnippet: `const pages = await vision.ocrBatch({
  documents: batch,
  languages: ["en", "es"],
  outputFormat: "text",
});`,
      },
      {
        name: "Extract Fields",
        description: "Document AI identifies structured fields — dates, names, reference numbers.",
        features: ["Document AI"],
        codeSnippet: `const fields = await vision.analyzeDocument({
  pages: pages,
  features: ["KEY_VALUE_DETECTION"],
});`,
      },
      {
        name: "Index",
        description: "Extracted text and fields are indexed for fast full-text and semantic search.",
        features: ["Custom Logic"],
        codeSnippet: `await searchIndex.addDocuments(
  fields.map(f => ({
    id: f.docId,
    text: f.fullText,
    metadata: f.keyValues,
  }))
);`,
      },
      {
        name: "Keyword Search",
        description: "Users query the index by keyword, date range, or field value.",
        features: ["Custom Logic"],
        codeSnippet: `const hits = await searchIndex.query({
  text: "contract renewal 2026",
  filters: { dateRange: ["2025-01", "2026-12"] },
  limit: 20,
});`,
      },
      {
        name: "Results",
        description: "Matching documents are returned with highlighted excerpts and confidence scores.",
        features: ["JSON Output"],
        codeSnippet: `return {
  totalHits: hits.total,
  documents: hits.results.map(h => ({
    title: h.title,
    excerpt: h.highlight,
    score: h.relevance,
  })),
};`,
      },
    ],
    cliCommand: "oci-vision workflow archive ./scans/ --demo",
  },
];

const ACCENT = "#34d399";
const ACCENT_DIM = "rgba(52,211,153,0.15)";
const ACCENT_BORDER = "rgba(52,211,153,0.5)";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function WorkflowPipelineWidget() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [completed, setCompleted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pipelineRef = useRef<HTMLDivElement>(null);

  const workflow = WORKFLOWS.find((w) => w.id === selectedId) ?? null;
  const stageCount = workflow?.stages.length ?? 0;

  /* ---- Cleanup on unmount ---- */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  /* ---- Animation stepper ---- */
  const stepForward = useCallback(
    (index: number, total: number) => {
      if (index >= total) {
        setCompleted(true);
        setRunning(false);
        return;
      }
      setActiveIndex(index);
      timerRef.current = setTimeout(() => stepForward(index + 1, total), 1000);
    },
    [],
  );

  /* ---- Select a workflow ---- */
  const handleSelect = useCallback((id: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setSelectedId(id);
    setRunning(false);
    setActiveIndex(-1);
    setCompleted(false);
  }, []);

  /* ---- Run / restart ---- */
  const handleRun = useCallback(() => {
    if (!workflow) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    setCompleted(false);
    setRunning(true);
    setActiveIndex(-1);
    // Small delay so UI can reset before animation starts
    timerRef.current = setTimeout(() => stepForward(0, workflow.stages.length), 150);
  }, [workflow, stepForward]);

  /* ---- Reset ---- */
  const handleReset = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setSelectedId(null);
    setRunning(false);
    setActiveIndex(-1);
    setCompleted(false);
  }, []);

  /* ---- Stage status helper ---- */
  const stageStatus = useCallback(
    (i: number): StageStatus => {
      if (completed) return "completed";
      if (i < activeIndex) return "completed";
      if (i === activeIndex) return "active";
      return "pending";
    },
    [activeIndex, completed],
  );

  /* ---- Collect all unique features for summary ---- */
  const allFeatures = workflow
    ? Array.from(new Set(workflow.stages.flatMap((s) => s.features)))
    : [];

  /* ---- Current stage for details panel ---- */
  const currentStage =
    workflow && activeIndex >= 0 && activeIndex < stageCount
      ? workflow.stages[activeIndex]
      : null;

  return (
    <div className="widget-container s8">
      {/* ---- Label ---- */}
      <div className="widget-label">Interactive &middot; Workflow Packs</div>

      {/* ---- Workflow selector buttons ---- */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.5rem",
          marginBottom: "1.5rem",
        }}
      >
        {WORKFLOWS.map((wf) => (
          <button
            key={wf.id}
            className={`btn-mono${selectedId === wf.id ? " active" : ""}`}
            onClick={() => handleSelect(wf.id)}
            style={
              selectedId === wf.id
                ? { borderColor: ACCENT_BORDER, color: ACCENT }
                : undefined
            }
          >
            <span>{wf.label}</span>
            <span
              style={{
                fontSize: "0.65rem",
                color: "#a1a1aa",
                marginLeft: "0.4rem",
                opacity: 0.7,
              }}
            >
              {wf.subtitle}
            </span>
          </button>
        ))}
      </div>

      {/* ---- Pipeline visualization ---- */}
      {workflow && (
        <>
          {/* Run / Reset controls */}
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              marginBottom: "1.25rem",
            }}
          >
            <button
              className="btn-mono"
              onClick={handleRun}
              disabled={running}
              style={
                running
                  ? { opacity: 0.4, cursor: "not-allowed" }
                  : { borderColor: ACCENT_BORDER, color: ACCENT }
              }
            >
              {completed ? "\u25B6 Replay" : "\u25B6 Run"}
            </button>
            <button className="btn-mono" onClick={handleReset}>
              Reset
            </button>
          </div>

          {/* Pipeline stages — horizontal scroll */}
          <div
            ref={pipelineRef}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 0,
              overflowX: "auto",
              paddingBottom: "0.5rem",
              marginBottom: "1.5rem",
            }}
          >
            {workflow.stages.map((stage, i) => {
              const status = stageStatus(i);
              return (
                <div
                  key={stage.name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <StageBox name={stage.name} status={status} />
                  {i < workflow.stages.length - 1 && (
                    <span
                      style={{
                        color:
                          status === "completed"
                            ? ACCENT
                            : "rgba(255,255,255,0.15)",
                        fontSize: "1.1rem",
                        margin: "0 0.3rem",
                        transition: "color 0.3s",
                        flexShrink: 0,
                      }}
                      aria-hidden="true"
                    >
                      &rarr;
                    </span>
                  )}
                </div>
              );
            })}
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

          {/* ---- Stage Details (while animating) ---- */}
          {currentStage && !completed && (
            <div
              key={`${workflow.id}-${activeIndex}`}
              style={{
                animation: "fadeSlideIn 0.35s ease-out both",
                marginBottom: "1.25rem",
              }}
            >
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
                Stage {activeIndex + 1} of {stageCount}
              </div>

              <div
                style={{
                  fontSize: "1rem",
                  fontWeight: 600,
                  color: ACCENT,
                  marginBottom: "0.35rem",
                }}
              >
                {currentStage.name}
              </div>

              <div
                style={{
                  fontSize: "0.85rem",
                  color: "#b4b4bc",
                  lineHeight: 1.7,
                  marginBottom: "0.75rem",
                }}
              >
                {currentStage.description}
              </div>

              {/* Feature badges */}
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "0.35rem",
                  marginBottom: "0.75rem",
                }}
              >
                {currentStage.features.map((f) => (
                  <FeatureBadge key={f} label={f} />
                ))}
              </div>

              {/* Code snippet */}
              <div className="code-block">
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                  <code style={{ color: "#e4e4e7" }}>
                    {currentStage.codeSnippet}
                  </code>
                </pre>
              </div>
            </div>
          )}

          {/* ---- Completion summary ---- */}
          {completed && (
            <div
              style={{
                animation: "fadeSlideIn 0.4s ease-out both",
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-mono), monospace",
                  fontSize: "0.7rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  color: ACCENT,
                  marginBottom: "0.75rem",
                }}
              >
                Pipeline Complete
              </div>

              {/* Summary card */}
              <div
                style={{
                  background: "rgba(0,0,0,0.3)",
                  border: `1px solid ${ACCENT_BORDER}`,
                  borderRadius: 10,
                  padding: "1.25rem",
                }}
              >
                {/* Features used */}
                <div
                  style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: "0.68rem",
                    color: "#a1a1aa",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.5rem",
                  }}
                >
                  Features Used
                </div>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "0.35rem",
                    marginBottom: "1rem",
                  }}
                >
                  {allFeatures.map((f) => (
                    <FeatureBadge key={f} label={f} />
                  ))}
                </div>

                {/* Total stages */}
                <div
                  style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: "0.68rem",
                    color: "#a1a1aa",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.35rem",
                  }}
                >
                  Total Stages
                </div>
                <div
                  style={{
                    fontSize: "1.1rem",
                    fontWeight: 700,
                    color: "#e4e4e7",
                    marginBottom: "1rem",
                  }}
                >
                  {stageCount}
                </div>

                {/* CLI command */}
                <div
                  style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: "0.68rem",
                    color: "#a1a1aa",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "0.5rem",
                  }}
                >
                  Try it
                </div>
                <div
                  className="code-block"
                  style={{
                    fontSize: "0.78rem",
                    padding: "0.75rem 1rem",
                  }}
                >
                  <code style={{ color: ACCENT }}>
                    $ {workflow.cliCommand}
                  </code>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ---- Empty state ---- */}
      {!workflow && (
        <div
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.78rem",
            color: "#a1a1aa",
            textAlign: "center",
            padding: "2rem 1rem",
          }}
        >
          Select a workflow above to explore its pipeline.
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  StageBox sub-component                                             */
/* ------------------------------------------------------------------ */

function StageBox({ name, status }: { name: string; status: StageStatus }) {
  const isPending = status === "pending";
  const isActive = status === "active";
  const isCompleted = status === "completed";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 100,
        padding: "0.65rem 0.75rem",
        borderRadius: 8,
        border: `1px solid ${
          isActive
            ? ACCENT_BORDER
            : isCompleted
              ? ACCENT_BORDER
              : "rgba(255,255,255,0.08)"
        }`,
        background: isCompleted
          ? ACCENT_DIM
          : isActive
            ? "rgba(52,211,153,0.05)"
            : "var(--card)",
        boxShadow: isActive ? `0 0 12px rgba(52,211,153,0.25)` : "none",
        animation: isActive ? "pulse-glow-emerald 1.5s ease-in-out infinite" : "none",
        transition: "all 0.35s ease",
        textAlign: "center",
        gap: "0.3rem",
      }}
    >
      {/* Checkmark or stage dot */}
      {isCompleted ? (
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="7" cy="7" r="6" fill={ACCENT} opacity={0.25} />
          <path
            d="M4 7.2L6 9.2L10 5"
            stroke={ACCENT}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <div
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: isActive ? ACCENT : "rgba(255,255,255,0.15)",
            transition: "background 0.3s",
          }}
        />
      )}

      <span
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.68rem",
          color: isPending ? "#a1a1aa" : isActive ? ACCENT : "#e4e4e7",
          lineHeight: 1.3,
          transition: "color 0.3s",
        }}
      >
        {name}
      </span>

      {/* Inline style tag for emerald pulse-glow keyframes */}
      <style>{`
        @keyframes pulse-glow-emerald {
          0%, 100% { box-shadow: 0 0 6px rgba(52,211,153,0.25); }
          50% { box-shadow: 0 0 18px rgba(52,211,153,0.5); }
        }
      `}</style>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  FeatureBadge sub-component                                         */
/* ------------------------------------------------------------------ */

function FeatureBadge({ label }: { label: string }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-mono), monospace",
        fontSize: "0.65rem",
        padding: "0.2rem 0.55rem",
        borderRadius: 4,
        background: ACCENT_DIM,
        color: ACCENT,
        border: `1px solid rgba(52,211,153,0.25)`,
        letterSpacing: "0.02em",
      }}
    >
      {label}
    </span>
  );
}
