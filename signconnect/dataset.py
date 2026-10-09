"""Tiny CSV helpers for the landmark dataset (data/landmarks.csv)."""
import csv
import os
import threading

from .features import FEATURE_COLUMNS

_lock = threading.Lock()


def append_sample(path, label, feats):
    with _lock:
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["label"] + FEATURE_COLUMNS)
            w.writerow([label] + [float(v) for v in feats])


def counts(path):
    result = {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for row in csv.reader(f):
                if row and row[0] != "label":
                    result[row[0]] = result.get(row[0], 0) + 1
    return result


def delete_label(path, label):
    with _lock:
        if not os.path.exists(path):
            return 0
        removed = 0
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        keep = [r for i, r in enumerate(rows) if i == 0 or r[0] != label]
        removed = len(rows) - len(keep)
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(keep)
        return removed
