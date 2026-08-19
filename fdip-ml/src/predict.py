import joblib

model = joblib.load("models/classifier.joblib")
vectorizer = joblib.load("models/tfidf_vectorizer.joblib")


def predict_document(text):
    document_tfidf = vectorizer.transform([text])

    prediction = model.predict(document_tfidf)
    probability = model.predict_proba(document_tfidf)

    predicted_class = prediction[0]
    confidence = float(probability[0].max())

    return {
        "document_type" : predicted_class,
        "confidence" : confidence
    }

new_document = """
ABC Electronics
Date: 18 August 2026

Laptop charger       1    2500.00
USB cable            2     400.00
Mouse                1     900.00

Subtotal: 3800.00
GST: 684.00
Total Amount: 4484.00

Payment Terms: Due within 30 days
Customer: XYZ Technologies
"""

result = predict_document(new_document)

print("Prediction: ", result)