"use client";

import {
  ClassificationWidget,
  ObjectDetectionWidget,
  OcrWidget,
  FaceDetectionWidget,
  DocumentAiWidget,
  EvalMetricsWidget,
  ArchitectureWidget,
  WorkflowPipelineWidget,
  PlaybackWidget,
  type PlaybackTrace,
} from "./components/widgets";

const visionPipelineTrace: PlaybackTrace = {
  source: `# OCI Vision AI request lifecycle
image = load("dog_closeup.jpg")            # 1. load bytes
tensor = preprocess(image)                 # 2. resize + normalize
response = vision.analyze_image(           # 3. call OCI Vision
    tensor,
    features=["LABEL_DETECTION", "OBJECT_DETECTION"],
)
overlay = annotate(image, response)        # 4. draw polygons
`,
  steps: [
    {
      line: 2,
      vars: { path: "dog_closeup.jpg", bytes: 184302 },
      note: "Read image bytes from disk into memory.",
    },
    {
      line: 3,
      vars: { width: 1024, height: 768, channels: 3 },
      note: "Preprocess: resize to model input, normalize pixel values to 0–1.",
    },
    {
      line: 4,
      vars: { features: ["LABEL_DETECTION", "OBJECT_DETECTION"], demo: true },
      note: "Send the tensor to OCI Vision (or the demo client) and await JSON.",
    },
    {
      line: 8,
      vars: { labels: 7, objects: 3, confidence_top: 0.94 },
      note: "Inference complete — labels and object polygons returned.",
    },
    {
      line: 9,
      vars: { polygons_drawn: 3, overlay: "ready" },
      note: "Annotate: draw bounding polygons and labels back onto the source image.",
    },
  ],
};

const sections = [
  { id: "classify", num: "01", title: "Classification" },
  { id: "detect", num: "02", title: "Detection" },
  { id: "ocr", num: "03", title: "OCR" },
  { id: "faces", num: "04", title: "Faces" },
  { id: "document", num: "05", title: "Document AI" },
  { id: "eval", num: "06", title: "Metrics" },
  { id: "arch", num: "07", title: "Architecture" },
  { id: "workflows", num: "08", title: "Workflows" },
];

const journey = [
  { num: "01", label: "Classify", desc: "Label images" },
  { num: "02", label: "Detect", desc: "Locate objects" },
  { num: "03", label: "Read", desc: "Extract text" },
  { num: "04", label: "Recognize", desc: "Find faces" },
  { num: "05", label: "Understand", desc: "Parse documents" },
  { num: "06", label: "Evaluate", desc: "Measure quality" },
  { num: "07", label: "Architect", desc: "Unified design" },
  { num: "08", label: "Compose", desc: "Build workflows" },
];

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* ---- Nav ---- */}
      <nav className="sticky top-0 z-50 bg-background border-b border-border">
        <div className="max-w-6xl mx-auto h-14 px-6 flex items-center gap-1 overflow-x-auto">
          <a href="#top" className="nav-link text-foreground mr-2">
            Vision<span className="text-muted-foreground">.play</span>
          </a>
          {sections.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="nav-link">
              <span className="text-muted-foreground">{s.num}</span>
              <span className="hidden md:inline ml-1">{s.title}</span>
            </a>
          ))}
        </div>
      </nav>

      {/* ---- Hero ---- */}
      <header id="top" className="border-b border-border py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-6">
          <p className="font-mono text-xs text-muted-foreground mb-4">Interactive explorer</p>
          <h1 className="text-4xl md:text-5xl font-medium tracking-tight leading-tight mb-6 max-w-3xl">
            OCI Vision AI, from the ground up
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl leading-relaxed">
            Eight sections, eight interactive widgets: image classification, object detection,
            OCR, face detection, document AI, evaluation metrics, the unified architecture and
            workflow packs.
          </p>
          <p className="text-xs text-muted-foreground mt-6 font-mono">
            Every concept below is interactive — drag sliders, toggle features, step through pipelines.
          </p>
        </div>
      </header>

      {/* ---- Table of contents ---- */}
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="bg-card border border-border rounded-2xl p-6">
          <h2 className="text-xs font-mono text-muted-foreground mb-4">Sections</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border hover:bg-white/5 transition-colors"
              >
                <span className="text-muted-foreground font-mono text-xs">{s.num}</span>
                <span className="text-sm">{s.title}</span>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* ---- Main content ---- */}
      <main className="max-w-6xl mx-auto px-6 pb-24 prose-dark">

        {/* ==== Pipeline playback ==== */}
        <section className="mb-16">
          <p className="font-mono text-xs text-muted-foreground mb-2">Before we dive in</p>
          <h2>Step through a Vision AI request</h2>
          <p>
            Every section below is a deep-dive into one feature. Under the hood, each call follows
            the same four-step lifecycle: <strong>load</strong> &rarr; <strong>preprocess</strong>{" "}
            &rarr; <strong>infer</strong> &rarr; <strong>annotate</strong>. Use the playback controls
            to walk through it.
          </p>
          <PlaybackWidget trace={visionPipelineTrace} label="Vision Pipeline" />
          <div className="section-divider" />
        </section>

        {/* ==== Section 1: Image classification ==== */}
        <section id="classify" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">01</span>
            <h2>Image Classification</h2>
          </div>
          <h3>Assign confidence-scored labels to any image</h3>
          <p>
            Image classification is the foundation of computer vision. Given an image, the OCI
            Vision API assigns one or more <strong>labels</strong> (like &ldquo;dog&rdquo;,
            &ldquo;outdoor&rdquo;, &ldquo;pet&rdquo;) along with a <strong>confidence score</strong>{" "}
            between 0 and 1. Higher scores mean the model is more certain about that label.
          </p>
          <p>
            In practice, you set a <strong>confidence threshold</strong> to filter out
            low-confidence predictions. Drag the slider below to see how threshold tuning affects
            which labels survive.
          </p>
          <ClassificationWidget />
          <p>
            Notice how raising the threshold progressively removes uncertain labels. A threshold of{" "}
            <code>0.5</code> is common for production use &mdash; it keeps labels the model is at
            least &ldquo;more likely than not&rdquo; confident about. The OCI Vision API returns up
            to 20 labels per image, each with an ontology-backed category path.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 2: Object detection ==== */}
        <section id="detect" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">02</span>
            <h2>Object Detection</h2>
          </div>
          <h3>Locate and classify objects with bounding polygons</h3>
          <p>
            While classification tells you <em>what</em> is in an image,{" "}
            <strong>object detection</strong> tells you <em>where</em>. The API returns bounding
            polygons with <strong>normalized vertices</strong> in the 0&ndash;1 coordinate space,
            which you then scale to pixel coordinates using the image dimensions.
          </p>
          <p>
            The quality of detections is measured using{" "}
            <strong>Intersection over Union (IoU)</strong> &mdash; how much the predicted bounding
            box overlaps with the ground truth. An IoU above 0.5 is typically considered a correct
            detection.
          </p>
          <ObjectDetectionWidget />
          <p>
            Each bounding polygon is defined by four normalized vertices. To convert to pixel
            coordinates, multiply by the image width and height:{" "}
            <code>pixel_x = norm_x &times; width</code>. The <code>human_position()</code> helper in
            the codebase converts these into readable descriptions like &ldquo;upper-left&rdquo; or
            &ldquo;center&rdquo;.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 3: Text / OCR ==== */}
        <section id="ocr" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">03</span>
            <h2>Text / OCR</h2>
          </div>
          <h3>Extract printed and handwritten text from images</h3>
          <p>
            Optical Character Recognition (<strong>OCR</strong>) extracts text from photos, scanned
            documents, and signs. The OCI Vision API returns a hierarchical structure:{" "}
            <strong>lines &rarr; words</strong>, each with its own bounding polygon and confidence
            score.
          </p>
          <p>
            Step through the pipeline below to see how OCR progressively breaks down an image into
            lines, segments words, and recognizes individual characters.
          </p>
          <OcrWidget />
          <p>
            The <code>TextDetectionResult</code> model provides a <code>full_text</code> computed
            property that concatenates all detected lines. Each <code>TextWord</code> carries its
            own confidence and bounding polygon, enabling precise overlay rendering with the
            built-in <code>renderer.py</code>.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 4: Face detection ==== */}
        <section id="faces" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">04</span>
            <h2>Face Detection</h2>
          </div>
          <h3>Detect faces and facial landmarks</h3>
          <p>
            <strong>Face detection</strong> locates faces in an image and identifies individual{" "}
            <strong>facial landmarks</strong> &mdash; eyes, nose, mouth, ears, and jaw points. All
            coordinates are normalized to the 0&ndash;1 range, making them resolution-independent.
          </p>
          <p>
            Toggle landmark groups below and hover each point to see its normalized and pixel
            coordinates. The <code>FaceLandmark</code> model includes a{" "}
            <code>human_position</code> property that describes each landmark&apos;s location in
            plain English.
          </p>
          <FaceDetectionWidget />
          <p>
            The <code>DetectedFace</code> model groups landmarks by type (eyes, nose, mouth, ears)
            and provides a <code>center</code> computed property for the face bounding box. In the
            web dashboard, the <code>renderer.py</code> draws landmark dots and connecting lines
            over the original image.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 5: Document AI ==== */}
        <section id="document" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">05</span>
            <h2>Document AI</h2>
          </div>
          <h3>Extract structured fields and tables from invoices, receipts, and forms</h3>
          <p>
            <strong>Document AI</strong> goes beyond simple OCR by understanding the{" "}
            <strong>semantic structure</strong> of documents. It identifies key fields (invoice
            number, date, totals) and extracts tabular data with row-column relationships.
          </p>
          <p>
            Step through the extraction pipeline below: from raw document to field detection to
            value extraction to structured JSON output.
          </p>
          <DocumentAiWidget />
          <p>
            The <code>DocumentResult</code> model carries both <code>fields</code> (key-value
            pairs) and <code>tables</code> (row-column structures). Each field includes its{" "}
            <code>confidence</code> score, enabling quality filtering before downstream use. The{" "}
            <code>receipt</code> workflow pack chains Document AI with validation logic for
            production invoice processing.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 6: Evaluation and metrics ==== */}
        <section id="eval" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">06</span>
            <h2>Evaluation and metrics</h2>
          </div>
          <h3>Measure, compare, and validate vision results</h3>
          <p>
            How do you know if your vision model is performing well? The project ships an{" "}
            <strong>evaluation lab</strong> with standard ML metrics:{" "}
            <strong>IoU</strong> for detection, <strong>precision/recall/F1</strong> for
            classification, and <strong>edit distance</strong> for OCR accuracy.
          </p>
          <p>
            Explore each metric below &mdash; drag boxes to see IoU change, adjust TP/FP/FN to
            understand precision-recall tradeoffs, or type text to see edit distance in action.
          </p>
          <EvalMetricsWidget />
          <p>
            The <code>eval/</code> module provides <code>intersection_over_union()</code>,{" "}
            <code>evaluate_detection_result()</code> with precision/recall/F1, and{" "}
            <code>normalized_edit_distance()</code> for OCR comparison. The{" "}
            <code>threshold_sweep()</code> function tests multiple confidence cutoffs and returns
            the optimal threshold for your use case.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 7: Architecture and demo mode ==== */}
        <section id="arch" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">07</span>
            <h2>Architecture and demo mode</h2>
          </div>
          <h3>One codebase, four surfaces, zero-credential learning</h3>
          <p>
            The entire project is built around a <strong>unified VisionClient</strong> that routes
            requests through either a <strong>DemoClient</strong> (offline, fixture-backed) or the{" "}
            <strong>real OCI SDK</strong>. Toggle the switch below to see how the code path changes.
          </p>
          <p>
            This same client powers all four delivery surfaces: CLI, Textual cockpit, FastAPI web
            dashboard, and Jupyter notebooks. Demo mode requires zero credentials &mdash; it serves
            cached responses from the gallery.
          </p>
          <ArchitectureWidget />
          <p>
            The demo-first design means anyone can explore every feature without an OCI account.
            Fixtures are recorded with <code>oci-vision record-demo</code> and served from{" "}
            <code>gallery/responses/</code>. The same Pydantic v2 models validate both demo and
            live responses, guaranteeing shape consistency.
          </p>
          <div className="section-divider" />
        </section>

        {/* ==== Section 8: Workflows ==== */}
        <section id="workflows" className="scroll-mt-16">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-muted-foreground font-mono text-sm">08</span>
            <h2>Workflow packs</h2>
          </div>
          <h3>Combine vision features into focused, production-ready pipelines</h3>
          <p>
            Individual vision features become powerful when <strong>composed into workflows</strong>
            . The project ships four production-ready workflow packs that chain multiple features
            together: receipt processing, shelf auditing, quality inspection, and document archive
            search.
          </p>
          <p>
            Select a workflow below and watch the pipeline animate through each stage, showing which
            vision features power each step.
          </p>
          <WorkflowPipelineWidget />
          <p>
            Each workflow is implemented as a focused Python module in <code>workflows/</code>. They
            compose the same <code>VisionClient</code> methods you&apos;ve explored above, adding
            domain-specific logic for validation, aggregation, and reporting. Run any workflow from
            the CLI: <code>oci-vision workflow receipt invoice.png --demo</code>.
          </p>
        </section>

        {/* ---- Conclusion ---- */}
        <section className="mt-16">
          <div className="bg-card border border-border rounded-2xl p-8">
            <h2 className="text-2xl font-medium mb-6">The journey</h2>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-12">
              {journey.map((step) => (
                <div
                  key={step.num}
                  className="flex items-baseline justify-between gap-6 py-2 border-b border-border"
                >
                  <dt className="font-mono text-sm">
                    <span className="text-muted-foreground mr-2">{step.num}</span>
                    {step.label}
                  </dt>
                  <dd className="text-xs text-muted-foreground">{step.desc}</dd>
                </div>
              ))}
            </dl>
            <p className="text-muted-foreground text-sm mt-6">
              From individual features to composed workflows &mdash; all explorable in demo mode,
              all production-ready with live OCI credentials.
            </p>
          </div>
        </section>
      </main>

      {/* ---- Footer ---- */}
      <footer className="border-t border-border py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <p className="text-sm text-muted-foreground">
            Built with Next.js, React 19, and Tailwind CSS. Part of the{" "}
            <a href="https://github.com/jasperan/oci-vision-ai" className="text-foreground underline underline-offset-2">
              OCI Vision AI
            </a>{" "}
            project.
          </p>
        </div>
      </footer>
    </div>
  );
}
