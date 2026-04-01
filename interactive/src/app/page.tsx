"use client";

import { useEffect } from "react";
import {
  ClassificationWidget,
  ObjectDetectionWidget,
  OcrWidget,
  FaceDetectionWidget,
  DocumentAiWidget,
  EvalMetricsWidget,
  ArchitectureWidget,
  WorkflowPipelineWidget,
} from "./components/widgets";

const sections = [
  { id: "classify", num: "01", title: "Classification", color: "text-s1" },
  { id: "detect", num: "02", title: "Detection", color: "text-s2" },
  { id: "ocr", num: "03", title: "OCR", color: "text-s3" },
  { id: "faces", num: "04", title: "Faces", color: "text-s4" },
  { id: "document", num: "05", title: "Document AI", color: "text-s5" },
  { id: "eval", num: "06", title: "Metrics", color: "text-s6" },
  { id: "arch", num: "07", title: "Architecture", color: "text-s7" },
  { id: "workflows", num: "08", title: "Workflows", color: "text-s8" },
];

export default function Home() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("visible");
        }),
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );
    document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen">
      {/* ---- Nav ---- */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-background/80 border-b border-border">
        <div className="max-w-5xl mx-auto px-4 py-2 flex items-center gap-1 overflow-x-auto">
          <a href="#top" className="nav-link font-bold text-foreground mr-2">
            Vision<span className="text-muted-foreground font-normal">.play</span>
          </a>
          {sections.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="nav-link">
              <span className={s.color}>{s.num}</span>
              <span className="hidden md:inline ml-1">{s.title}</span>
            </a>
          ))}
        </div>
      </nav>

      {/* ---- Hero ---- */}
      <header id="top" className="relative overflow-hidden py-24 md:py-32">
        <div className="hero-glow bg-orange-500 top-[-200px] left-[10%]" />
        <div className="hero-glow bg-cyan-500 top-[-100px] right-[15%]" />
        <div className="hero-glow bg-purple-500 bottom-[-200px] left-[40%]" />
        <div className="max-w-5xl mx-auto px-4 relative z-10">
          <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase mb-4">
            Interactive Explorer
          </p>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-tight mb-6">
            <span className="text-s1">See</span>.{" "}
            <span className="text-s2">Detect</span>.{" "}
            <span className="text-s3">Read</span>.{" "}
            <span className="text-s5">Extract</span>.{" "}<br className="hidden md:block" />
            OCI <span className="text-s7">Vision AI</span> from the Ground Up
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl leading-relaxed">
            Eight sections. Eight interactive widgets. One journey through{" "}
            <span className="text-s1">image classification</span>,{" "}
            <span className="text-s2">object detection</span>,{" "}
            <span className="text-s3">OCR</span>,{" "}
            <span className="text-s4">face detection</span>,{" "}
            <span className="text-s5">document AI</span>,{" "}
            <span className="text-s6">evaluation metrics</span>,{" "}
            <span className="text-s7">unified architecture</span>, and{" "}
            <span className="text-s8">workflow packs</span>.
          </p>
          <p className="text-sm text-muted-foreground mt-4 font-mono">
            Every concept below is interactive. Drag sliders, toggle features, step through pipelines.
          </p>
        </div>
      </header>

      {/* ---- Table of Contents ---- */}
      <div className="max-w-5xl mx-auto px-4 mb-16">
        <div className="bg-card border border-border rounded-xl p-6">
          <h2 className="text-sm font-mono text-muted-foreground uppercase tracking-wider mb-4">
            Sections
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border hover:bg-white/5 transition-colors"
              >
                <span className={`${s.color} font-mono text-sm font-bold`}>{s.num}</span>
                <span className="text-sm">{s.title}</span>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* ---- Main Content ---- */}
      <main className="max-w-5xl mx-auto px-4 pb-24 prose-dark">

        {/* ==== Section 1: Image Classification ==== */}
        <section id="classify" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s1 font-mono text-sm font-bold">01</span>
            <h2 className="text-s1">Image Classification</h2>
          </div>
          <h3>Assign confidence-scored labels to any image</h3>
          <p>
            Image classification is the foundation of computer vision. Given an image, the OCI Vision API assigns
            one or more <span className="text-s1">labels</span>{" "}(like &ldquo;dog&rdquo;, &ldquo;outdoor&rdquo;,
            &ldquo;pet&rdquo;) along with a <strong>confidence score</strong> between 0 and 1.
            Higher scores mean the model is more certain about that label.
          </p>
          <p>
            In practice, you set a <span className="text-s1">confidence threshold</span> to filter out
            low-confidence predictions. Drag the slider below to see how threshold tuning affects which
            labels survive.
          </p>
          <ClassificationWidget />
          <p>
            Notice how raising the threshold progressively removes uncertain labels.
            A threshold of <code>0.5</code> is common for production use &mdash; it keeps labels the model
            is at least &ldquo;more likely than not&rdquo; confident about. The OCI Vision API returns
            up to 20 labels per image, each with an ontology-backed category path.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 2: Object Detection ==== */}
        <section id="detect" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s2 font-mono text-sm font-bold">02</span>
            <h2 className="text-s2">Object Detection</h2>
          </div>
          <h3>Locate and classify objects with bounding polygons</h3>
          <p>
            While classification tells you <em>what</em> is in an image, <span className="text-s2">object
            detection</span> tells you <em>where</em>. The API returns bounding polygons with
            <strong>normalized vertices</strong> in the 0&ndash;1 coordinate space, which you then
            scale to pixel coordinates using the image dimensions.
          </p>
          <p>
            The quality of detections is measured using <span className="text-s2">Intersection over
            Union (IoU)</span> &mdash; how much the predicted bounding box overlaps with the ground truth.
            An IoU above 0.5 is typically considered a correct detection.
          </p>
          <ObjectDetectionWidget />
          <p>
            Each bounding polygon is defined by four normalized vertices. To convert to pixel coordinates,
            multiply by the image width and height: <code>pixel_x = norm_x &times; width</code>.
            The <code>human_position()</code> helper in the codebase converts these into readable
            descriptions like &ldquo;upper-left&rdquo; or &ldquo;center&rdquo;.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 3: Text / OCR ==== */}
        <section id="ocr" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s3 font-mono text-sm font-bold">03</span>
            <h2 className="text-s3">Text / OCR</h2>
          </div>
          <h3>Extract printed and handwritten text from images</h3>
          <p>
            Optical Character Recognition (<span className="text-s3">OCR</span>) extracts text from photos,
            scanned documents, and signs. The OCI Vision API returns a hierarchical structure:
            <strong> lines &rarr; words</strong>, each with its own bounding polygon and
            confidence score.
          </p>
          <p>
            Step through the pipeline below to see how OCR progressively breaks down
            an image into lines, segments words, and recognizes individual characters.
          </p>
          <OcrWidget />
          <p>
            The <code>TextDetectionResult</code> model provides a <code>full_text</code> computed
            property that concatenates all detected lines. Each <code>TextWord</code> carries its
            own confidence and bounding polygon, enabling precise overlay rendering
            with the built-in <code>renderer.py</code>.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 4: Face Detection ==== */}
        <section id="faces" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s4 font-mono text-sm font-bold">04</span>
            <h2 className="text-s4">Face Detection</h2>
          </div>
          <h3>Detect faces and facial landmarks</h3>
          <p>
            <span className="text-s4">Face detection</span> locates faces in an image and identifies
            individual <strong>facial landmarks</strong> &mdash; eyes, nose, mouth, ears, and jaw points.
            All coordinates are normalized to the 0&ndash;1 range, making them resolution-independent.
          </p>
          <p>
            Toggle landmark groups below and hover each point to see its normalized and pixel coordinates.
            The <code>FaceLandmark</code> model includes a <code>human_position</code> property
            that describes each landmark&apos;s location in plain English.
          </p>
          <FaceDetectionWidget />
          <p>
            The <code>DetectedFace</code> model groups landmarks by type (eyes, nose, mouth, ears)
            and provides a <code>center</code> computed property for the face bounding box.
            In the web dashboard, the <code>renderer.py</code> draws landmark dots and connecting
            lines over the original image.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 5: Document AI ==== */}
        <section id="document" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s5 font-mono text-sm font-bold">05</span>
            <h2 className="text-s5">Document AI</h2>
          </div>
          <h3>Extract structured fields and tables from invoices, receipts, and forms</h3>
          <p>
            <span className="text-s5">Document AI</span> goes beyond simple OCR by understanding
            the <strong>semantic structure</strong> of documents. It identifies key fields
            (invoice number, date, totals) and extracts tabular data with row-column relationships.
          </p>
          <p>
            Step through the extraction pipeline below: from raw document to field detection
            to value extraction to structured JSON output.
          </p>
          <DocumentAiWidget />
          <p>
            The <code>DocumentResult</code> model carries both <code>fields</code> (key-value pairs)
            and <code>tables</code> (row-column structures). Each field includes its
            <code>confidence</code> score, enabling quality filtering before downstream use.
            The <code>receipt</code> workflow pack chains Document AI with validation logic
            for production invoice processing.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 6: Evaluation & Metrics ==== */}
        <section id="eval" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s6 font-mono text-sm font-bold">06</span>
            <h2 className="text-s6">Evaluation & Metrics</h2>
          </div>
          <h3>Measure, compare, and validate vision results</h3>
          <p>
            How do you know if your vision model is performing well? The project ships an
            <span className="text-s6"> evaluation lab</span> with standard ML metrics:
            <strong> IoU</strong> for detection, <strong>precision/recall/F1</strong> for
            classification, and <strong>edit distance</strong> for OCR accuracy.
          </p>
          <p>
            Explore each metric below &mdash; drag boxes to see IoU change, adjust TP/FP/FN
            to understand precision-recall tradeoffs, or type text to see edit distance in action.
          </p>
          <EvalMetricsWidget />
          <p>
            The <code>eval/</code> module provides <code>intersection_over_union()</code>,
            <code>evaluate_detection_result()</code> with precision/recall/F1, and
            <code>normalized_edit_distance()</code> for OCR comparison.
            The <code>threshold_sweep()</code> function tests multiple confidence cutoffs
            and returns the optimal threshold for your use case.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 7: Architecture & Demo Mode ==== */}
        <section id="arch" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s7 font-mono text-sm font-bold">07</span>
            <h2 className="text-s7">Architecture & Demo Mode</h2>
          </div>
          <h3>One codebase, four surfaces, zero-credential learning</h3>
          <p>
            The entire project is built around a <span className="text-s7">unified
            VisionClient</span> that routes requests through either a <strong>DemoClient</strong>
            (offline, fixture-backed) or the <strong>real OCI SDK</strong>. Toggle the switch
            below to see how the code path changes.
          </p>
          <p>
            This same client powers all four delivery surfaces: CLI, Textual cockpit,
            FastAPI web dashboard, and Jupyter notebooks. Demo mode requires
            zero credentials &mdash; it serves cached responses from the gallery.
          </p>
          <ArchitectureWidget />
          <p>
            The demo-first design means anyone can explore every feature without an OCI account.
            Fixtures are recorded with <code>oci-vision record-demo</code> and served from
            <code>gallery/responses/</code>. The same Pydantic v2 models validate both
            demo and live responses, guaranteeing shape consistency.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 8: Workflows ==== */}
        <section id="workflows" className="scroll-mt-16 reveal">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-s8 font-mono text-sm font-bold">08</span>
            <h2 className="text-s8">Workflow Packs</h2>
          </div>
          <h3>Combine vision features into focused, production-ready pipelines</h3>
          <p>
            Individual vision features become powerful when <span className="text-s8">composed
            into workflows</span>. The project ships four production-ready workflow packs
            that chain multiple features together: receipt processing, shelf auditing,
            quality inspection, and document archive search.
          </p>
          <p>
            Select a workflow below and watch the pipeline animate through each stage,
            showing which vision features power each step.
          </p>
          <WorkflowPipelineWidget />
          <p>
            Each workflow is implemented as a focused Python module in <code>workflows/</code>.
            They compose the same <code>VisionClient</code> methods you&apos;ve explored above,
            adding domain-specific logic for validation, aggregation, and reporting.
            Run any workflow from the CLI: <code>oci-vision workflow receipt invoice.png --demo</code>.
          </p>
        </section>

        {/* ---- Conclusion ---- */}
        <section className="mt-16 reveal">
          <div className="bg-card border border-border rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">The Journey</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { num: "01", label: "Classify", color: "text-s1", desc: "Label images" },
                { num: "02", label: "Detect", color: "text-s2", desc: "Locate objects" },
                { num: "03", label: "Read", color: "text-s3", desc: "Extract text" },
                { num: "04", label: "Recognize", color: "text-s4", desc: "Find faces" },
                { num: "05", label: "Understand", color: "text-s5", desc: "Parse documents" },
                { num: "06", label: "Evaluate", color: "text-s6", desc: "Measure quality" },
                { num: "07", label: "Architect", color: "text-s7", desc: "Unified design" },
                { num: "08", label: "Compose", color: "text-s8", desc: "Build workflows" },
              ].map((step) => (
                <div key={step.num} className="text-center py-3">
                  <div className={`${step.color} font-mono text-lg font-bold`}>{step.num}</div>
                  <div className="text-sm font-semibold mt-1">{step.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{step.desc}</div>
                </div>
              ))}
            </div>
            <p className="text-muted-foreground text-sm mt-6 text-center">
              From individual features to composed workflows &mdash; all explorable in demo mode,
              all production-ready with live OCI credentials.
            </p>
          </div>
        </section>
      </main>

      {/* ---- Footer ---- */}
      <footer className="border-t border-border py-12 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <p className="text-sm text-muted-foreground">
            Built with Next.js, React 19, and Tailwind CSS.
            Part of the{" "}
            <a
              href="https://github.com/jasperan/oci-vision-ai"
              className="text-s7 hover:underline"
            >
              OCI Vision AI
            </a>{" "}
            project.
          </p>
        </div>
      </footer>
    </div>
  );
}
