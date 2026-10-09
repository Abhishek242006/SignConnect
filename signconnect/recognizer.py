"""Hand detection (MediaPipe) + gesture classification (trained scikit-learn model)."""
import json
import os
import sys
import threading

import cv2
import numpy as np
import joblib

from .features import normalize_landmarks, landmarks_to_list
from .vocabulary import EMERGENCY_WORDS

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE, "models", "gesture_model.joblib")
REPORT_PATH = os.path.join(BASE, "models", "evaluation_report.json")
CONFIDENCE_THRESHOLD = 0.70  # below this a gesture is reported as "unknown"


def fix_message(version):
    what = "MediaPipe is not installed" if version is None else f"MediaPipe {version} has no 'solutions' API"
    return (f'{what} in this Python. Stop the server (Ctrl+C) and run: '
            f'"{sys.executable}" -m pip install mediapipe==0.10.14 "numpy<2" "opencv-python<4.11" , then start the app again.')


class Recognizer:
    def __init__(self, model_path=MODEL_PATH, threshold=CONFIDENCE_THRESHOLD):
        self.threshold = threshold
        self.model = None
        self.model_path = model_path
        self._hands = None
        self._lock = threading.Lock()
        self.load_model()

    def load_model(self):
        self.model = joblib.load(self.model_path) if os.path.exists(self.model_path) else None
        return self.model is not None

    @property
    def classes(self):
        return list(self.model.classes_) if self.model is not None else []

    def _get_hands(self):
        if self._hands is None:
            try:
                import mediapipe as mp  # imported lazily so the app starts without it
            except ImportError as exc:
                raise RuntimeError(fix_message(None)) from exc
            if not hasattr(mp, "solutions"):
                raise RuntimeError(fix_message(mp.__version__))
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=1,
                min_detection_confidence=0.6, min_tracking_confidence=0.5)
        return self._hands

    def classify(self, points):
        """Classify 21 landmarks. Returns (word_or_None, confidence)."""
        if self.model is None:
            return None, 0.0
        proba = self.model.predict_proba([normalize_landmarks(points)])[0]
        best = int(np.argmax(proba))
        conf = float(proba[best])
        word = str(self.model.classes_[best])
        return (word if conf >= self.threshold else None), conf

    def extract(self, frame):
        """Return 21 (x, y, z) landmarks for the first hand in a BGR frame, or None."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        with self._lock:
            result = self._get_hands().process(rgb)
        if not result.multi_hand_landmarks:
            return None
        return landmarks_to_list(result.multi_hand_landmarks[0])

    def process_bgr(self, frame):
        """Full pipeline for one BGR frame. Everything runs locally."""
        out = {"model_loaded": self.model is not None, "hand_detected": False,
               "landmarks": [], "word": None, "confidence": 0.0, "emergency": False}
        points = self.extract(frame)
        if points is None:
            return out
        out["hand_detected"] = True
        out["landmarks"] = xy(points)
        word, conf = self.classify(points)
        out["word"], out["confidence"] = word, round(conf, 3)
        out["emergency"] = word in EMERGENCY_WORDS
        return out


def xy(points):
    return [[round(x, 4), round(y, 4)] for x, y, _ in points]


def load_report():
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH) as f:
            return json.load(f)
    return None
