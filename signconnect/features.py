"""Landmark -> feature vector conversion (shared by collection, training and the app)."""
import numpy as np

NUM_LANDMARKS = 21
NUM_FEATURES = NUM_LANDMARKS * 3  # x, y, z for each landmark
FEATURE_COLUMNS = [f"{axis}{i}" for i in range(NUM_LANDMARKS) for axis in "xyz"]


def normalize_landmarks(points):
    """Make features independent of hand position and size.

    1. Translate so the wrist (landmark 0) is the origin.
    2. Scale so the largest x/y distance from the wrist is 1.
    Returns a flat float32 array of length 63.
    """
    arr = np.asarray(points, dtype=np.float32).reshape(NUM_LANDMARKS, 3)
    arr = arr - arr[0]
    scale = np.abs(arr[:, :2]).max()
    if scale > 0:
        arr = arr / scale
    return arr.flatten()


def landmarks_to_list(hand_landmarks):
    """Convert a MediaPipe hand_landmarks object to [(x, y, z), ...]."""
    return [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
