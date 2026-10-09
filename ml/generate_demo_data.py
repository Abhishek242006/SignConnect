"""Generate SYNTHETIC landmark data (random prototypes + noise).

FOR TESTING THE PIPELINE ONLY. A model trained on this data does NOT recognise
real sign language. Use ml/collect_data.py to build a real dataset.
"""
import argparse
import numpy as np
import pandas as pd

from signconnect.features import FEATURE_COLUMNS
from signconnect.vocabulary import WORDS


def generate(path, per_class=120, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for word in WORDS:
        proto = rng.normal(0, 0.6, len(FEATURE_COLUMNS))
        for _ in range(per_class):
            rows.append([word] + (proto + rng.normal(0, 0.05, len(proto))).tolist())
    pd.DataFrame(rows, columns=["label"] + FEATURE_COLUMNS).to_csv(path, index=False)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/synthetic_demo.csv")
    ap.add_argument("--per-class", type=int, default=120)
    a = ap.parse_args()
    print("Wrote", generate(a.out, a.per_class), "(synthetic - pipeline testing only)")
