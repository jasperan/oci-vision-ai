/**
 * OCI Vision Studio — client-side JavaScript.
 *
 * Handles drag-and-drop image upload, the plate preview, feature toggle
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
    const resultStatus = document.getElementById("result-status");

    if (!dropZone || !fileInput) return; // not on the analyzer page

    const plate = { name: "", width: 0, height: 0 };

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
        dropZone.classList.add("dragging");
    });

    dropZone.addEventListener("dragleave", function (e) {
        e.preventDefault();
        dropZone.classList.remove("dragging");
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.classList.remove("dragging");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileInput.files = e.dataTransfer.files;
            showPreview(e.dataTransfer.files[0]);
        }
    });

    // ------------------------------------------------------------------
    // Plate preview
    // ------------------------------------------------------------------
    function showPreview(file) {
        if (!file.type.startsWith("image/")) return;
        plate.name = file.name;
        const reader = new FileReader();
        reader.onload = function (e) {
            preview.src = e.target.result;
            preview.classList.remove("hidden");
            if (dropText) dropText.classList.add("hidden");
            preview.onload = function () {
                plate.width = preview.naturalWidth;
                plate.height = preview.naturalHeight;
            };
        };
        reader.readAsDataURL(file);
    }

    function plateLabel() {
        const name = plate.name || "uploaded image";
        const size = plate.width && plate.height ? ` · ${plate.width}×${plate.height}` : "";
        return `plate 01 · ${name}${size}`;
    }

    // ------------------------------------------------------------------
    // HTMX response handling — render JSON results as structured HTML
    // ------------------------------------------------------------------
    document.body.addEventListener("htmx:beforeSwap", function (evt) {
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

        if (data.overlay_base64) {
            html += '<figure class="plate-frame" style="margin:0">';
            html += '<figcaption class="plate">' + escHtml(plateLabel()) + "</figcaption>";
            html += '<img id="analysis-overlay" src="data:image/png;base64,' + data.overlay_base64 + '" class="overlay-img" alt="Annotated image" />';
            if (data.feature_overlays && Object.keys(data.feature_overlays).length) {
                html += '<div class="feature-tabs">';
                html += '<button type="button" class="chip active" onclick="window.__ociVisionSetOverlay(\'' + data.overlay_base64 + '\', this)">All features</button>';
                Object.keys(data.feature_overlays).forEach(function (featureName) {
                    html += '<button type="button" class="chip" onclick="window.__ociVisionSetOverlay(\'' + data.feature_overlays[featureName] + '\', this)">' + escHtml(featureName) + "</button>";
                });
                html += "</div>";
            }
            html += "</figure>";
        }

        if (data.insights && data.insights.length) {
            html += '<div class="result-section">';
            html += '<h3 class="result-title">Insights</h3>';
            html += '<ul class="report-list">';
            data.insights.forEach(function (line) {
                html += "<li>" + escHtml(line) + "</li>";
            });
            html += "</ul></div>";
        }

        if (data.classification && data.classification.labels) {
            html += '<div class="result-section">';
            html += '<h3 class="result-title">Classification</h3>';
            html += '<div class="result-list">';
            data.classification.labels.slice(0, 10).forEach(function (label, index) {
                const pct = (label.confidence * 100).toFixed(1);
                html += '<div class="result-row">';
                html += '<span class="name">' + escHtml(label.name) + "</span>";
                html += '<span class="value">' + pct + "%</span>";
                html += '<div class="bar"><div class="bar-fill' + (index === 0 ? " top" : "") + '" style="width:' + pct + '%"></div></div>';
                html += "</div>";
            });
            html += "</div></div>";
        }

        if (data.detection && data.detection.objects) {
            html += '<div class="result-section">';
            html += '<h3 class="result-title">Detection</h3>';
            html += '<div class="result-list">';
            data.detection.objects.forEach(function (object) {
                const pct = (object.confidence * 100).toFixed(1);
                html += '<div class="detection-row"><span>' + escHtml(object.name) + '</span><span class="value">' + pct + "%</span></div>";
            });
            html += "</div></div>";
        }

        if (data.text && data.text.lines) {
            html += '<div class="result-section">';
            html += '<h3 class="result-title">Text</h3>';
            html += '<pre class="text-block">' + escHtml(data.text.full_text) + "</pre>";
            html += "</div>";
        }

        if (data.faces && data.faces.faces) {
            html += '<div class="result-section">';
            html += '<h3 class="result-title">Faces</h3>';
            html += '<dl class="kv"><dt>Faces</dt><dd>' + data.faces.faces.length + "</dd></dl>";
            html += "</div>";
        }

        if (data.document) {
            html += '<div class="result-section">';
            html += '<h3 class="result-title">Document</h3>';
            if (data.document.fields && data.document.fields.length) {
                html += '<dl class="kv">';
                data.document.fields.forEach(function (field) {
                    html += "<dt>" + escHtml(field.label) + "</dt><dd>" + escHtml(field.value) + "</dd>";
                });
                html += "</dl>";
            } else {
                html += '<p class="small muted">No document fields returned.</p>';
            }
            html += "</div>";
        }

        html += '<details class="api-details">';
        html += '<summary>Raw response</summary>';
        html += '<div class="api-body">';
        html += '<pre class="code">' + escHtml(JSON.stringify(data, null, 2)) + "</pre>";
        html += "</div></details>";

        const elapsed = (data.elapsed_seconds || 0).toFixed(3);
        html += '<div class="meta-line">' + elapsed + "s";
        if (data.available_features && data.available_features.length) {
            html += " · " + escHtml(data.available_features.join(" · "));
        }
        html += "</div>";

        if (resultStatus) {
            resultStatus.textContent = "analysis · " + elapsed + "s";
        }

        return html || '<p class="small muted">No results returned.</p>';
    }

    window.__ociVisionSetOverlay = function (base64Payload, button) {
        const img = document.getElementById("analysis-overlay");
        if (img) {
            img.src = "data:image/png;base64," + base64Payload;
        }
        if (button) {
            document.querySelectorAll(".feature-tabs .chip").forEach(function (chip) {
                chip.classList.remove("active");
            });
            button.classList.add("active");
        }
    };

    function escHtml(str) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }
})();
