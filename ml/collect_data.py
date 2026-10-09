"""Collect labelled hand-landmark samples from your webcam.

Run:  python -m ml.collect_data
Keys: SPACE start/stop recording | N next sign | P previous sign | Q quit
Samples are appended to data/landmarks.csv (label + 63 normalized features).
Tip: record >= 150 samples per sign, varying distance, angle and lighting,
ideally with several different people.
"""
import csv
import os
import cv2
import mediapipe as mp

from signconnect.features import FEATURE_COLUMNS, normalize_landmarks, landmarks_to_list
from signconnect.vocabulary import WORDS

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "landmarks.csv")
TARGET = 200


def main():
    new_file = not os.path.exists(OUT)
    f = open(OUT, "a", newline="")
    writer = csv.writer(f)
    if new_file:
        writer.writerow(["label"] + FEATURE_COLUMNS)
    counts = {w: 0 for w in WORDS}
    idx, recording = 0, False
    hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.6)
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        word = WORDS[idx]
        if res.multi_hand_landmarks:
            hl = res.multi_hand_landmarks[0]
            mp.solutions.drawing_utils.draw_landmarks(frame, hl, mp.solutions.hands.HAND_CONNECTIONS)
            if recording and counts[word] < TARGET:
                writer.writerow([word] + normalize_landmarks(landmarks_to_list(hl)).tolist())
                counts[word] += 1
        status = f"{word}  {counts[word]}/{TARGET}  {'REC' if recording else 'paused'}"
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.imshow("SignConnect data collection", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            recording = not recording
        elif key == ord("n"):
            idx, recording = (idx + 1) % len(WORDS), False
        elif key == ord("p"):
            idx, recording = (idx - 1) % len(WORDS), False
    cap.release(); cv2.destroyAllWindows(); f.close()
    print("Saved to", OUT, counts)


if __name__ == "__main__":
    main()
