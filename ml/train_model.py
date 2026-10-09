"""Train, compare and save gesture classifiers.

Run:  python -m ml.train_model --data data/landmarks.csv
Outputs (in models/): gesture_model.joblib, evaluation_report.json, confusion_matrix.png
"""
import argparse
import json
import os

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, precision_recall_fscore_support)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

MIN_PER_CLASS = 10


def candidate_models():
    return {
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
        "SVM (RBF)": make_pipeline(StandardScaler(), SVC(probability=True, random_state=42)),
        "KNN": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5)),
        "Neural Network (MLP)": make_pipeline(
            StandardScaler(), MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42)),
    }


def train(data_path, out_dir="models"):
    df = pd.read_csv(data_path)
    counts = df["label"].value_counts()
    if len(counts) < 2:
        raise ValueError("Record at least 2 different signs before training.")
    if counts.min() < MIN_PER_CLASS:
        raise ValueError(f"Each sign needs >= {MIN_PER_CLASS} samples. Low: {counts[counts < MIN_PER_CLASS].to_dict()}")
    X, y = df.drop(columns="label").values, df["label"].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    results, fitted = {}, {}
    for name, model in candidate_models().items():
        cv = cross_val_score(model, X_tr, y_tr, cv=5).mean()
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        p, r, f1, _ = precision_recall_fscore_support(y_te, pred, average="weighted", zero_division=0)
        results[name] = {"accuracy": accuracy_score(y_te, pred), "precision": p, "recall": r,
                         "f1": f1, "cv_accuracy": cv}
        fitted[name] = (model, pred)
        print(f"{name:22s} acc={results[name]['accuracy']:.3f} f1={f1:.3f} cv={cv:.3f}")

    best = max(results, key=lambda n: (results[n]["f1"], results[n]["cv_accuracy"]))
    model, pred = fitted[best]
    labels = sorted(set(y))
    cm = confusion_matrix(y_te, pred, labels=labels)

    os.makedirs(out_dir, exist_ok=True)
    joblib.dump(model, os.path.join(out_dir, "gesture_model.joblib"))
    report = {"best_model": best, "classes": labels, "n_samples": int(len(df)),
              "samples_per_class": {k: int(v) for k, v in counts.items()},
              "models": results, "confusion_matrix": cm.tolist()}
    with open(os.path.join(out_dir, "evaluation_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=90)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(f"Confusion matrix - {best}")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out_dir, "confusion_matrix.png"), dpi=120); plt.close(fig)
    print("Best model:", best, "-> saved to", out_dir)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/landmarks.csv")
    ap.add_argument("--out-dir", default="models")
    a = ap.parse_args()
    train(a.data, a.out_dir)
