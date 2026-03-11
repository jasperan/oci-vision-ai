"""Render visual overlays (bounding boxes, landmarks, OCR highlights,
classification labels) on images using Pillow.

Takes a PIL Image and an AnalysisReport, returns a **new** RGB PIL Image
with the overlays composited on top.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from oci_vision.core.models import AnalysisReport

# ---------------------------------------------------------------------------
# Colour palette – 8 distinct colours cycled for object classes
# ---------------------------------------------------------------------------
_PALETTE: list[tuple[int, int, int]] = [
    (255, 0, 0),       # red
    (0, 200, 0),       # green
    (0, 120, 255),     # blue
    (255, 165, 0),     # orange
    (200, 0, 200),     # magenta
    (0, 200, 200),     # cyan
    (255, 255, 0),     # yellow
    (180, 105, 255),   # light purple
]

_FACE_LANDMARK_COLOR = (80, 120, 255)   # blue
_OCR_HIGHLIGHT_COLOR = (255, 255, 0)    # yellow
_LABEL_BG_COLOR = (0, 0, 0, 160)        # semi-transparent black
_LABEL_TEXT_COLOR = (255, 255, 255, 255) # white

_BOX_WIDTH = 2
_LANDMARK_RADIUS = 4

# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

def _load_font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try DejaVu Sans, fall back to Pillow default."""
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Internal drawing helpers
# ---------------------------------------------------------------------------

def _text_bbox(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    """Return (width, height) of rendered *text* using *font*."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text_color: tuple[int, ...] = _LABEL_TEXT_COLOR,
    bg_color: tuple[int, ...] = _LABEL_BG_COLOR,
    pad: int = 3,
) -> None:
    """Draw *text* at (*x*, *y*) with a semi-transparent background pill."""
    tw, th = _text_bbox(draw, text, font)
    draw.rectangle(
        [x, y, x + tw + 2 * pad, y + th + 2 * pad],
        fill=bg_color,
    )
    draw.text((x + pad, y + pad), text, fill=text_color, font=font)


def _draw_detections(
    draw: ImageDraw.ImageDraw,
    report: AnalysisReport,
    img_w: int,
    img_h: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    if report.detection is None:
        return
    seen_names: dict[str, int] = {}
    for obj in report.detection.objects:
        # Assign a colour index per unique class name
        if obj.name not in seen_names:
            seen_names[obj.name] = len(seen_names)
        color = _PALETTE[seen_names[obj.name] % len(_PALETTE)]
        rgba_color = (*color, 255)

        pixels = obj.bounding_polygon.to_pixels(img_w, img_h)
        if len(pixels) >= 2:
            draw.polygon(pixels, outline=rgba_color)
            # Thicken by drawing multiple offset polygons
            for offset in range(1, _BOX_WIDTH):
                shifted = [(x + offset, y + offset) for x, y in pixels]
                draw.polygon(shifted, outline=rgba_color)

        # Label: "Name XX%" at top of bounding box
        pct = round(obj.confidence * 100)
        label = f"{obj.name} {pct}%"
        top_x = min(p[0] for p in pixels) if pixels else 0
        top_y = min(p[1] for p in pixels) if pixels else 0
        tw, th = _text_bbox(draw, label, font)
        # Position label just above the box (or at box top if no room)
        label_y = max(0, top_y - th - 8)
        _draw_label(draw, label, top_x, label_y, font, text_color=(*color, 255))


def _draw_classification(
    draw: ImageDraw.ImageDraw,
    report: AnalysisReport,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    if report.classification is None:
        return
    # Show the top labels as floating tags at top-left, stacked vertically
    x, y = 8, 8
    for label in report.classification.labels[:5]:  # cap at 5 for readability
        pct = round(label.confidence * 100)
        text = f"{label.name} {pct}%"
        tw, th = _text_bbox(draw, text, font)
        _draw_label(draw, text, x, y, font)
        y += th + 10


def _draw_text_regions(
    draw: ImageDraw.ImageDraw,
    report: AnalysisReport,
    img_w: int,
    img_h: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    if report.text is None:
        return
    highlight = (*_OCR_HIGHLIGHT_COLOR, 50)  # semi-transparent yellow
    outline = (*_OCR_HIGHLIGHT_COLOR, 200)
    for line in report.text.lines:
        pixels = line.bounding_polygon.to_pixels(img_w, img_h)
        if len(pixels) >= 2:
            draw.polygon(pixels, fill=highlight, outline=outline)
        # Draw extracted text label above the region
        top_x = min(p[0] for p in pixels) if pixels else 0
        top_y = min(p[1] for p in pixels) if pixels else 0
        _draw_label(draw, line.text, top_x, max(0, top_y - 18), font)


def _draw_faces(
    draw: ImageDraw.ImageDraw,
    report: AnalysisReport,
    img_w: int,
    img_h: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    if report.faces is None:
        return
    face_outline = (*_FACE_LANDMARK_COLOR, 200)
    landmark_fill = (*_FACE_LANDMARK_COLOR, 255)
    for face in report.faces.faces:
        # Bounding box
        pixels = face.bounding_polygon.to_pixels(img_w, img_h)
        if len(pixels) >= 2:
            draw.polygon(pixels, outline=face_outline)
            for offset in range(1, _BOX_WIDTH):
                shifted = [(x + offset, y + offset) for x, y in pixels]
                draw.polygon(shifted, outline=face_outline)

        # Confidence label
        pct = round(face.confidence * 100)
        label = f"Face {pct}%"
        top_x = min(p[0] for p in pixels) if pixels else 0
        top_y = min(p[1] for p in pixels) if pixels else 0
        tw, th = _text_bbox(draw, label, font)
        _draw_label(draw, label, top_x, max(0, top_y - th - 8), font)

        # Landmarks as filled circles
        r = _LANDMARK_RADIUS
        for lm in face.landmarks:
            cx = int(lm.x * img_w)
            cy = int(lm.y * img_h)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=landmark_fill)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_overlay(image: Image.Image, report: AnalysisReport) -> Image.Image:
    """Composite visual overlays onto *image* based on *report*.

    Returns a **new** RGB :class:`~PIL.Image.Image` – the original is
    never mutated.
    """
    # Early-out: nothing to draw
    if not report.available_features:
        return image.convert("RGB")

    img_w, img_h = image.size
    font = _load_font(max(12, img_h // 40))

    # Work on an RGBA copy so we can alpha-composite
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Layer order: text regions first (they have semi-transparent fill),
    # then detection boxes, faces, and finally classification tags on top.
    _draw_text_regions(draw, report, img_w, img_h, font)
    _draw_detections(draw, report, img_w, img_h, font)
    _draw_faces(draw, report, img_w, img_h, font)
    _draw_classification(draw, report, font)

    composited = Image.alpha_composite(base, overlay)
    return composited.convert("RGB")
