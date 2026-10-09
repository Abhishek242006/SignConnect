"""Download one real ISL clip per sign from the Hugging Face dataset and save it for the Learn page.

Run:  python tools/fetch_learn_videos.py
Writes static/signs/videos/<slug>.mp4 + ATTRIBUTION.txt

Licences: the dataset is an AGGREGATE of sources with different licences (INCLUDE CC-BY-4.0, CISLR AFL-3.0,
ISLRTC MIT, ISL500 'see its card'). By default only the first three are used. Add --allow-isl500 only after
you have read the ISL500 licence. The mp4 files are git-ignored so you do not re-distribute them.
"""
import argparse
import os
import shutil
import sys

import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signconnect.vocabulary import SIGNS  # noqa: E402

# SignConnect word -> word in the dataset (None = the dataset has no such sign)
WORD_MAP = {"Hello": "hello", "Thank You": "thank you", "Yes": "yes", "No": "no", "Help": "help",
            "Please": "please", "Stop": "stop", "Water": "water", "Food": "food", "Sorry": "sorry",
            "I": "me", "You": "you", "Good": None, "Bad": None, "Emergency": None, "Doctor": None, "Call": None}
PREFERRED = ["include", "cislr", "islrtc"]        # clear open licences
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "signs", "videos")


def pick(df, word, allow_isl500):
    rows = df[df["normalized_word"].str.lower() == word]
    if "review_status" in rows:
        rows = rows[rows["review_status"].astype(str).str.lower() == "accepted"]
    src = rows["dataset"].astype(str).str.lower()
    allowed = PREFERRED + (["isl500"] if allow_isl500 else [])
    rows = rows[src.apply(lambda s: any(s.startswith(a) for a in allowed))].copy()
    if rows.empty:
        return None
    order = {a: i for i, a in enumerate(allowed)}
    rows["_rank"] = rows["dataset"].astype(str).str.lower().apply(
        lambda s: next(order[a] for a in allowed if s.startswith(a)))
    return rows.sort_values(["_rank", "quality_score", "duration"], ascending=[True, False, True]).iloc[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Angirekula/isl-isolated-40words",
                    help="if this fails try vidit031/isl-isolated-40words (the id used in the dataset card's example)")
    ap.add_argument("--allow-isl500", action="store_true")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    meta = pd.read_csv(hf_hub_download(a.repo, "metadata.csv", repo_type="dataset"))
    credits, missing = [], []
    for s in SIGNS:
        word = WORD_MAP.get(s["word"])
        row = pick(meta, word, a.allow_isl500) if word else None
        if row is None:
            missing.append(s["word"])
            continue
        src = hf_hub_download(a.repo, row["video_path"], repo_type="dataset")
        shutil.copyfile(src, os.path.join(OUT, s["slug"] + ".mp4"))
        credits.append(f'{s["word"]}: {row["dataset"]} clip "{row["original_filename"]}" | licence: {row["license"]} | '
                       f'source: {row["repository"]}')
        print("ok  ", s["word"], "<-", row["dataset"])
    with open(os.path.join(OUT, "ATTRIBUTION.txt"), "w", encoding="utf-8") as f:
        f.write(f"Sign videos from https://huggingface.co/datasets/{a.repo} (derived aggregate of upstream datasets).\n"
                "Please cite and respect each upstream licence.\n\n" + "\n".join(credits) + "\n")
    print("\nNo usable clip for:", ", ".join(missing) or "none",
          "(those keep the photo/illustration; drop your own static/signs/videos/<slug>.mp4 to add one)")


if __name__ == "__main__":
    main()
