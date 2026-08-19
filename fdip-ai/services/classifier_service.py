from pathlib import Path
import joblib

BASE_DIR = Path(__file__).resolve().parents[2]

model = joblib.load(
    BASE_DIR / "fdip-ml" / "models" / "classifier.joblib"
)

vectorizer = joblib.load(
    BASE_DIR / "fdip-ml" / "models" / "tfidf_vectorizer.joblib"
)


def predict_document(text):
    document_tfidf = vectorizer.transform([text])

    prediction = model.predict(document_tfidf)
    probability = model.predict_proba(document_tfidf)

    return {
        "document_type": prediction[0],
        "confidence": float(probability[0].max())
    }