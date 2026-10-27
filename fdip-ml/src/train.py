import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression



from pathlib import Path

# project root directory (fdip-ml)
BASE_DIR = Path(__file__).resolve().parent.parent

# dataset location
DATASET_PATH = BASE_DIR / "datasets" / "processed" / "classifier_dataset.csv"

df = pd.read_csv(DATASET_PATH)

print("Dataset loaded successfully!")
print("Dataset shape:", df.shape)



X_text = df["text"]
y = df["label"]


# splitting
X_train_text, X_test_text, y_train, y_test = train_test_split(
    X_text,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)



vectorizer = TfidfVectorizer()


# Learn TF-IDF vocabulary from training data
X_train = vectorizer.fit_transform(X_train_text)


# Transform test data using the same vocabulary
X_test = vectorizer.transform(X_test_text)


print("Training:", X_train.shape)
print("Testing:", X_test.shape)

model = LogisticRegression(max_iter=1000)

model.fit(X_train,y_train)

print("Model Trained!")

new_document = [
    "#INV-000001 Zylker Design Labs Balance Due 14B, Northern Street $18,400.00 Greater South Avenue New York 10001 U.S.A Bill To Jack Little 3242 Chandler Hollow Road Pittsburgh 15222 Pennsylvania Ship To 3242 Chandler Hollow Road Pittsburgh Invoice Date: 05 Aug 2024 15222 Pennsylvania Terms: Due on Receipt # Item & Description Qty Rate Amount 1 Brochure Design 1.00 900.00 900.00 Brochure design - Single sided (Color) 2 Web Design packages (Simple) 1.00 10,000.00 10,000.00 10 Pages, Slider, Free Logo, Dynamic Website, Free Domain, Hosting Free for 1st year, 3 Print Ad - Newspaper 1.00 7,500.00 7,500.00 A full-page ad, Nationwide Circulation (Colour) Sub Total 18,400.00 Tax Rate 5.00% Total $19320.00 Notes Thanks for your business. Balance Due $19320.00 Terms & Conditions All payments must be made in full before the commencement of any design work."
]

new_document_tfidf = vectorizer.transform(new_document)

prediction = model.predict(new_document_tfidf)

print("Prediction:", prediction[0])

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

predictions = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, predictions))

print("\nClassification Report:")
print(classification_report(y_test, predictions))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, predictions))

import joblib

MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)



joblib.dump(model, MODEL_DIR / "classifier.joblib")
joblib.dump(vectorizer, MODEL_DIR / "tfidf_vectorizer.joblib")

print("Model saved!")