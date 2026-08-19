from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
from io import BytesIO
import fitz


ocr = PaddleOCR(
    device="cpu",

    # Use lightweight PP-OCRv5 models
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",

    # Skip expensive preprocessing
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,

    enable_hpi=False
)


def ocr_image(image):
    """Run PaddleOCR on a single image."""

    result = ocr.predict(image)

    page = result[0]

    return "\n".join(page["rec_texts"])


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