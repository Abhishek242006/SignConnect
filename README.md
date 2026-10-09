# 🤟 SignConnect – Real-Time Sign Language to Text and Speech

Webcam → MediaPipe hand landmarks → trained scikit-learn classifier → text → speech.
Theme: **Inclusive Technology**. Architecture diagram: [docs/architecture.md](docs/architecture.md).

## Honest scope (please read)
* The repo ships **code, not a pre-trained model or real dataset**. You record your own landmark data, then train.
  Until a model exists the app says so and recognises nothing – it never fakes results.
* The 17 gestures are **project-defined static one-hand shapes**, not official ASL/ISL. Real signs often use motion
  and two hands; extending to those needs sequence models (see Future work).
* `ml/generate_demo_data.py` makes *synthetic* data only to test the training pipeline. Don't use it for demos.

## Setup
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt                       # Python 3.9–3.12
```
## Easiest path: do everything in the browser
`python app.py` → open **Train** → Start camera → pick a sign, press **Record**, move your hand slightly until the bar
fills (150 samples) → repeat for each sign → **Train model** → open **Translator**. Without a trained model the app only
tracks the hand (green skeleton) and says that no model exists.

## 1) Collect data (alternative: command line; SPACE record · N/P next/prev sign · Q quit)
```bash
python -m ml.collect_data          # writes data/landmarks.csv  (aim for 150–200 samples/sign, several people & lighting)
```
## 2) Train & compare models
```bash
python -m ml.train_model --data data/landmarks.csv
```
Trains Random Forest, SVM, KNN, MLP; prints accuracy / precision / recall / F1 / 5-fold CV, picks the best by F1,
and saves `models/gesture_model.joblib`, `models/evaluation_report.json`, `models/confusion_matrix.png`.
## 3) Run
```bash
python app.py       # open http://127.0.0.1:5000  (camera needs localhost or https)
```
## 4) Test
```bash
python -m unittest discover -s tests -t .
```

## Features
Home · Train (record + train in the browser) · Translator (live overlay, gesture, confidence, sentence, speak, undo, clear, pause/resume) · History (SQLite) ·
Learn Signs (illustrated hand shapes + webcam practice) · About (shows real evaluation results). Extras: emergency warning for Help/Emergency,
multi-language speech (English, Hindi, Tamil, Spanish, French via a built-in word dictionary + browser voices – voice
availability depends on your OS/browser), confidence threshold (0.70) for unknown gestures, high-contrast mode,
A- / A+ text size buttons, skip link, keyboard shortcuts (Space/S/C), responsive layout.

## Adding a sign
1. Add an entry in `signconnect/vocabulary.py` (+ translations in `static/js/translator.js`).
2. `python -m ml.collect_data` → record it.  3. `python -m ml.train_model`.  4. Restart the app.

## API
| Method | Path | Description |
|---|---|---|
| POST | `/api/predict` | `{"image": "<base64 JPEG>"}` → `{model_loaded, hand_detected, landmarks, word, confidence, emergency}`; `word` is `null` if below threshold. 400 bad input, 503 MediaPipe problem |
| GET | `/api/vocabulary` | Defined signs + classes the loaded model was actually trained on |
| GET | `/api/model-info` | Threshold + evaluation report |
| GET / POST | `/api/history` | List / add `{"sentence": "..."}` |
| DELETE | `/api/history/<id>` · `/api/history` | Delete one / all |

| POST | `/api/collect` | `{"image","label","record"}` → saves one normalized sample when `record` is true |
| GET / DELETE | `/api/dataset` · `/api/dataset/<label>` | Sample counts / delete a sign's samples |
| POST | `/api/train` | Trains + compares models, saves best, reloads it |
| GET | `/api/status` | MediaPipe OK?, model loaded?, trained classes |

Sign illustrations: `python tools/make_sign_images.py` regenerates `static/signs/*.svg` (replace with real photos if you like).

## Real sign videos on the Learn page (optional)
```bash
python -m pip install huggingface_hub
python tools/fetch_learn_videos.py          # one clip per sign -> static/signs/videos/ + ATTRIBUTION.txt
```
Source: Hugging Face `Angirekula/isl-isolated-40words` (ISL clips aggregated from INCLUDE, CISLR, ISLRTC, ISL500, each with its own
licence – read the dataset card, cite the sources, and don't commit the mp4s). Signs without a clip (Good, Bad, Emergency,
Doctor, Call) keep the photo/illustration. Any `static/signs/videos/<slug>.mp4` or `.webm` you add is used automatically. You can also film your own demo clip per sign with **Train → 🎥 Record demo video** (it overrides a downloaded clip).

## Tamil / other-language speech
The browser speaks with voices installed on your device. If a language has none (often Tamil), the app falls back to an online
voice (`/api/tts`, needs `python -m pip install gTTS` and internet; only the sentence text is sent). For fully offline speech use
Microsoft Edge or add the voice in Windows → Settings → Time & language → Speech.

## Troubleshooting
* Hand skeleton not drawn → camera permission, or MediaPipe: `pip install mediapipe==0.10.14`. The Translator shows the exact error.
* Skeleton drawn but no word → you haven't trained yet, or confidence is below 70% (shows “Unknown”). Record more varied samples.
* `no attribute 'solutions'` → `pip install mediapipe==0.10.14`.
* Low accuracy → more varied data; keep the same hand/camera setup used for recording.
* Landmarks are not mirror-normalised: record and use the same hand.

## Future work
Two-hand features, sequence model (LSTM) for motion signs, user accounts, more languages, mobile app.
