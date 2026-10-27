import re
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
from io import BytesIO
import fitz


ocr = PaddleOCR(
    device="cpu",

    # use lightweight PP-OCRv5 models
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",

    #skip expensive preprocessing
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,

    enable_hpi=False
)




def _page_boxes(page):
    """Return an (N, 4) array of [x1, y1, x2, y2] boxes for the recognised lines."""
    boxes = page.get("rec_boxes")
    if boxes is not None and len(boxes) > 0:
        return np.asarray(boxes, dtype=float).reshape(-1, 4)

    polys = page.get("rec_polys")
    if polys is None or len(polys) == 0:
        polys = page.get("dt_polys")

    arr = np.asarray(polys, dtype=float)          # (N, 4, 2)
    return np.stack(
        [arr[:, :, 0].min(1), arr[:, :, 1].min(1),
         arr[:, :, 0].max(1), arr[:, :, 1].max(1)],
        axis=1,
    )


_LABEL_LIKE = re.compile(r"[A-Za-z][A-Za-z /.&()#\-]{1,40}")


def _layout_text(texts, boxes):
    """Group OCR boxes into visual rows (top-to-bottom, left-to-right) so that
    table cells that sit side by side end up on the same line."""

    items = [
        (str(t).strip(), b) for t, b in zip(texts, boxes) if str(t).strip()
    ]
    if not items:
        return ""

    heights = [b[3] - b[1] for _, b in items]
    median_h = float(np.median(heights)) or 1.0

    items.sort(key=lambda it: (it[1][1] + it[1][3]) / 2)

    rows = []
    for text, b in items:
        cy = (b[1] + b[3]) / 2
        if rows and abs(cy - rows[-1]["cy"]) <= 0.6 * median_h:
            row = rows[-1]
            n = len(row["cells"])
            row["cy"] = (row["cy"] * n + cy) / (n + 1)
            row["cells"].append((b, text))
        else:
            rows.append({"cy": cy, "cells": [(b, text)]})

    lines = []
    for row in rows:
        cells = sorted(row["cells"], key=lambda c: c[0][0])
        parts = [cells[0][1]]

        for (prev_b, prev_t), (b, t) in zip(cells, cells[1:]):
            parts.append(t)

        line = parts[0]
        for i in range(1, len(parts)):
            gap = cells[i][0][0] - cells[i - 1][0][2]
            sep = " "
            # "Label        value" -> "Label : value" (only for short key/value
            # rows, not for wide table header/data rows)
            if (i == 1 and len(cells) <= 3 and gap > 1.5 * median_h
                    and not parts[0].rstrip().endswith(":")
                    and _LABEL_LIKE.fullmatch(parts[0].strip())):
                sep = " : "
            line += sep + parts[i]
        lines.append(line)

    return "\n".join(lines)


def ocr_image(image):
    """Run PaddleOCR on a single image."""

    result = ocr.predict(image)

    page = result[0]

    texts = page["rec_texts"]

    try:
        boxes = _page_boxes(page)
        if len(boxes) != len(texts):
            raise ValueError("box/text count mismatch")
        return _layout_text(texts, boxes)
    except Exception:
        # never lose the OCR output if layout reconstruction fails
        return "\n".join(texts)


def extract_pdf_text(file_bytes):
    """Render every PDF page and run OCR on it."""

    pdf = fitz.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number, pdf_page in enumerate(pdf, start=1):

        # Render PDF page at 2x resolution
        pix = pdf_page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )

        # Convert rendered page into NumPy image
        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        ).reshape(
            pix.height,
            pix.width,
            pix.n
        )

        # OCR the page
        text = ocr_image(image)

        pages.append(
            f"--- Page {page_number} ---\n{text}"
        )

    pdf.close()

    return "\n\n".join(pages)


def extract_text(file_bytes, content_type):

    if content_type == "application/pdf":
        return extract_pdf_text(file_bytes)

    if not content_type.startswith("image/"):
        return {
            "error": "Unsupported file type"
        }

    image = Image.open(
        BytesIO(file_bytes)
    ).convert("RGB")

    image = np.array(image)

    return ocr_image(image)