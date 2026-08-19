from fastapi import FastAPI, UploadFile, File
from services.ocr_service import extract_text
from services.classifier_service import predict_document

app = FastAPI(
    title="FDIP AI Service",
    version="1.0.0",
    description="OCR and AI service for the Financial Document Intelligence Platform"
)

@app.get("/")
def root():
    return {
        "status": "healthy"
    }

@app.post("/extract")
def extract(file: UploadFile = File(...)):
    contents = file.file.read()
    text = extract_text(contents, file.content_type)
    classification = predict_document(text)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size" : len(contents),
        "text" : text,
        "document_type" : classification["document_type"],
        "confidence" : classification["confidence"],
    }