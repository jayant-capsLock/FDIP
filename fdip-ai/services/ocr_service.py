from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
from io import BytesIO

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

def extract_text(file_bytes, content_type):

    if content_type == "application/pdf":
        return {
            "status": "PDF pipeline not implemented yet"
        }

    if not content_type.startswith("image/"):
        return {
            "error": "Unsupported file type"
        }

    image = Image.open(BytesIO(file_bytes)).convert("RGB")
    image = np.array(image)

    result = ocr.predict(image)

    page = result[0]

    text = "\n".join(page["rec_texts"])

    return {
        "text": text,
        "confidence": page["rec_scores"]
    }