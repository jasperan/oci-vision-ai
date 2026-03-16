/**
 * OCI Vision Studio — client-side JavaScript.
 *
 * Handles drag-and-drop image upload, file preview, feature toggle
 * synchronisation, and HTMX response rendering.
 */
(function () {
    "use strict";

    // ------------------------------------------------------------------
    // DOM references
    // ------------------------------------------------------------------
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const preview = document.getElementById("preview");
    const dropText = document.getElementById("drop-text");
    const featuresInput = document.getElementById("features-input");

    if (!dropZone || !fileInput) return; // not on the analyzer page

    // ------------------------------------------------------------------
    // Feature checkboxes -> hidden input sync
    // ------------------------------------------------------------------
    function syncFeatures() {
        const checked = document.querySelectorAll(
            'input[type="checkbox"][name^="feat_"]:checked'
        );
        const values = Array.from(checked).map((cb) => cb.value);
        if (featuresInput) {
            featuresInput.value = values.join(",");
        }
    }

    document.querySelectorAll('input[type="checkbox"][name^="feat_"]').forEach(
        (cb) => cb.addEventListener("change", syncFeatures)
    );
    // Initial sync
    syncFeatures();

    // ------------------------------------------------------------------
    // Click-to-browse
    // ------------------------------------------------------------------
    dropZone.addEventListener("click", function () {
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        if (fileInput.files && fileInput.files[0]) {
            showPreview(fileInput.files[0]);
        }
    });

    // ------------------------------------------------------------------
    // Drag-and-drop
    // ------------------------------------------------------------------
    dropZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZone.classList.add("border-cyan-400", "bg-cyan-900/20");
    });

    dropZone.addEventListener("dragleave", function (e) {
        e.preventDefault();
        dropZone.classList.remove("border-cyan-400", "bg-cyan-900/20");
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.classList.remove("border-cyan-400", "bg-cyan-900/20");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileInput.files = e.dataTransfer.files;
            showPreview(e.dataTransfer.files[0]);
        }
    });

    // ------------------------------------------------------------------
    // File preview
    // ------------------------------------------------------------------
    function showPreview(file) {
        if (!file.type.startsWith("image/")) return;
        const reader = new FileReader();
        reader.onload = function (e) {
            preview.src = e.target.result;
            preview.classList.remove("hidden");
            if (dropText) dropText.classList.add("hidden");
        };
        reader.readAsDataURL(file);
    }

    // ------------------------------------------------------------------
    // HTMX response handling — render JSON results as structured HTML
    // ------------------------------------------------------------------
    document.body.addEventListener("htmx:beforeSwap", function (evt) {
        // The /api/analyze-upload endpoint returns JSON.
        // We intercept and render it as HTML before HTMX swaps.
        if (evt.detail.xhr && evt.detail.xhr.responseURL &&
            evt.detail.xhr.responseURL.includes("/api/analyze-upload")) {
            try {
                const data = JSON.parse(evt.detail.xhr.responseText);
                evt.detail.serverResponse = renderResults(data);
            } catch (e) {
                // If not JSON, let HTMX handle it as-is
            }
        }
    });

    /**
     * Render analysis JSON into HTML for the results panel.
     */
    function renderResults(data) {
        let html = "";

        // Overlay image + toggle buttons
        if (data.overlay_base64) {
            html += '<div class="mb-4">';
            html += '<h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Overlay</h3>';
            html += '<img id="analysis-overlay" src="data:image/png;base64,' + data.overlay_base64 + '" class="w-full rounded-lg border border-slate-600 mb-3" alt="Annotated" />';
            if (data.feature_overlays && Object.keys(data.feature_overlays).length) {
                html += '<div class="flex flex-wrap gap-2">';
                html += '<button type="button" class="text-xs px-3 py-1 rounded-full bg-cyan-900/50 text-cyan-300 border border-cyan-700/40" onclick="window.__ociVisionSetOverlay(\'' + data.overlay_base64 + '\')">All</button>';
                Object.keys(data.feature_overlays).forEach(function (featureName) {
                    html += '<button type="button" class="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-200 border border-slate-700" onclick="window.__ociVisionSetOverlay(\'' + data.feature_overlays[featureName] + '\')">' + escHtml(featureName) + '</button>';
                });
                html += '</div>';
            }
            html += "</div>";
        }

        // Classification
        if (data.classification && data.classification.labels) {
            html += '<div class="mb-4">';
            html += '<h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Classification</h3>';
            html += '<div class="space-y-1">';
            data.classification.labels.slice(0, 10).forEach(function (l) {
                const pct = (l.confidence * 100).toFixed(1);
                html += '<div class="flex items-center justify-between text-sm"><span>' + escHtml(l.name) + '</span><span class="cyan-accent font-mono">' + pct + '%</span></div>';
                html += '<div class="w-full bg-slate-700 rounded-full h-1.5"><div class="cyan-bg rounded-full h-1.5" style="width:' + pct + '%"></div></div>';
            });
            html += "</div></div>";
        }

        // Detection
        if (data.detection && data.detection.objects) {
            html += '<div class="mb-4">';
            html += '<h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Object Detection</h3>';
            html += '<div class="space-y-2">';
            data.detection.objects.forEach(function (o) {
                const pct = (o.confidence * 100).toFixed(1);
                html += '<div class="flex items-center justify-between text-sm bg-slate-800/50 rounded px-3 py-2"><span class="font-medium">' + escHtml(o.name) + '</span><span class="cyan-accent font-mono">' + pct + '%</span></div>';
            });
            html += "</div></div>";
        }

        // Text / OCR
        if (data.text && data.text.lines) {
            html += '<div class="mb-4">';
            html += '<h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Text / OCR</h3>';
            html += '<div class="bg-slate-800/50 rounded p-3 text-sm font-mono whitespace-pre-wrap">' + escHtml(data.text.full_text) + "</div>";
            html += "</div>";
        }

        // Faces
        if (data.faces && data.faces.faces) {
            html += '<div class="mb-4">';
            html += '<h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Face Detection</h3>';
            html += "<p class=\"text-sm\">" + data.faces.faces.length + " face(s) detected</p>";
            html += "</div>";
        }

        // Document
        if (data.document) {
            html += '<div class="mb-4">';
            html += '<h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Document AI</h3>';
            if (data.document.fields && data.document.fields.length) {
                html += '<div class="space-y-2">';
                data.document.fields.forEach(function (field) {
                    html += '<div class="text-sm bg-slate-800/50 rounded px-3 py-2"><span class="font-medium">' + escHtml(field.label) + '</span>: ' + escHtml(field.value) + '</div>';
                });
                html += '</div>';
            }
            html += '</div>';
        }

        // API playground
        html += '<details class="mt-4 rounded-lg border border-slate-700 bg-slate-900/50">';
        html += '<summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-300">API Playground</summary>';
        html += '<div class="px-4 pb-4">';
        html += '<p class="text-xs text-slate-500 mb-2">Raw normalized JSON response</p>';
        html += '<pre class="overflow-x-auto whitespace-pre-wrap text-xs text-slate-200">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
        html += '</div></details>';

        // Footer
        html += '<div class="text-xs text-slate-500 mt-4">';
        html += "Elapsed: " + (data.elapsed_seconds || 0).toFixed(3) + "s";
        if (data.available_features && data.available_features.length) {
            html += " &bull; Features: " + data.available_features.join(", ");
        }
        html += "</div>";

        return html || '<p class="text-slate-500">No results returned.</p>';
    }

    window.__ociVisionSetOverlay = function (base64Payload) {
        const img = document.getElementById("analysis-overlay");
        if (img) {
            img.src = "data:image/png;base64," + base64Payload;
        }
    };

    function escHtml(str) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }
})();
