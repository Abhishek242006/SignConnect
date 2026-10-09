# Architecture

```mermaid
flowchart LR
  A[Browser webcam<br/>getUserMedia] -->|JPEG frame, ~8 fps<br/>localhost only| B[Flask /api/predict]
  B --> C[OpenCV decode]
  C --> D[MediaPipe Hands<br/>21 landmarks]
  D --> E[Normalize<br/>wrist-origin, unit scale]
  E --> F[Trained classifier<br/>joblib model]
  F -->|word + confidence| G{confidence >= 0.70?}
  G -- no --> H[Unknown - ignored]
  G -- yes --> I[JSON response]
  I --> J[Browser: overlay + smoothing<br/>+ sentence builder]
  J --> K[Web Speech API<br/>multi-language TTS]
  J --> L[(SQLite history)]
```

```
signconnect/
├── app.py                  Flask app + REST API
├── signconnect/            vocabulary, features, recognizer (MediaPipe + model)
├── ml/                     collect_data, train_model, generate_demo_data
├── templates/ static/      Home, Translator, History, Learn, About UI
├── data/  models/          landmarks.csv, history.db | trained model + reports
└── tests/                  unittest suites
```

Offline/private: Flask, MediaPipe and the model all run on your machine. Nothing is sent to external servers.
