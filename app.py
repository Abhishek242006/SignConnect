"""SignConnect Flask backend. Run: python app.py  ->  http://127.0.0.1:5000"""
import base64
import io
import os
import sqlite3
import sys
from datetime import datetime

import cv2
import numpy as np
from werkzeug.exceptions import HTTPException
from flask import Flask, send_file, g, jsonify, render_template, request, send_from_directory, url_for

from signconnect import dataset
from signconnect.features import normalize_landmarks
from signconnect.recognizer import Recognizer, fix_message, load_report, xy
from signconnect.vocabulary import SIGNS, WORDS

BASE = os.path.dirname(os.path.abspath(__file__))


def decode_image(data):
    try:
        raw = (data or {}).get("image", "")
        return cv2.imdecode(np.frombuffer(base64.b64decode(raw.split(",")[-1]), np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return None


def create_app(db_path=None, recognizer=None, data_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.path.join(BASE, "data", "history.db")
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
    app.config["DATA_PATH"] = data_path or os.path.join(BASE, "data", "landmarks.csv")
    rec = recognizer or Recognizer()

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                         " sentence TEXT NOT NULL, created_at TEXT NOT NULL)")
        return g.db

    @app.teardown_appcontext
    def close_db(_):
        conn = g.pop("db", None)
        if conn:
            conn.close()

    def signs_view():
        """Signs + best available picture: your own photo if captured, else the illustration."""
        out = []
        for sg in SIGNS:
            photo = os.path.join(BASE, "static", "signs", "photos", sg["slug"] + ".jpg")
            if os.path.exists(photo):
                img = url_for("static", filename=f"signs/photos/{sg['slug']}.jpg") + f"?v={int(os.path.getmtime(photo))}"
            else:
                img = url_for("static", filename=f"signs/{sg['slug']}.svg")
            video = None
            for ext in ("webm", "mp4"):
                vid = os.path.join(BASE, "static", "signs", "videos", f"{sg['slug']}.{ext}")
                if os.path.exists(vid):
                    video = url_for("static", filename=f"signs/videos/{sg['slug']}.{ext}") + f"?v={int(os.path.getmtime(vid))}"
                    break
            out.append(dict(sg, img=img, photo=os.path.exists(photo), video=video))
        return out

    @app.errorhandler(Exception)
    def on_error(exc):  # API errors are always JSON so the UI can show the real message
        if request.path.startswith("/api/"):
            return jsonify(error=str(exc)), (exc.code if isinstance(exc, HTTPException) else 500)
        if isinstance(exc, HTTPException):
            return exc
        raise exc

    # ---------- pages ----------
    @app.route("/")
    def home():
        return render_template("home.html", page="home")

    @app.route("/translator")
    def translator():
        return render_template("translator.html", page="translator")

    @app.route("/train")
    def train():
        return render_template("train.html", page="train", signs=signs_view())

    @app.route("/history")
    def history():
        return render_template("history.html", page="history")

    @app.route("/learn")
    def learn():
        return render_template("learn.html", page="learn", signs=signs_view(),
                               credit=os.path.exists(os.path.join(BASE, "static", "signs", "videos", "ATTRIBUTION.txt")))

    @app.route("/about")
    def about():
        return render_template("about.html", page="about", report=load_report(), signs=SIGNS,
                               samples=dataset.counts(app.config["DATA_PATH"]))

    @app.route("/help", endpoint="help")
    def help_page():
        return render_template("help.html", page="help")

    @app.route("/model/confusion_matrix.png")
    def confusion_png():
        return send_from_directory(os.path.dirname(rec.model_path), "confusion_matrix.png")

    # ---------- API ----------
    @app.get("/api/status")
    def status():
        """Self-check used by the UI to explain why nothing is being recognised."""
        try:
            import mediapipe as mp
            mp_ok, ver = hasattr(mp, "solutions"), mp.__version__
        except ImportError:
            mp_ok, ver = False, None
        return jsonify(mediapipe_ok=mp_ok, mediapipe_version=ver, python=sys.executable,
                       fix=None if mp_ok else fix_message(ver), model_loaded=rec.model is not None, trained_classes=rec.classes,
                       threshold=rec.threshold, samples=dataset.counts(app.config["DATA_PATH"]))

    @app.post("/api/predict")
    def predict():
        """Body: {"image": "<data-URL or base64 JPEG>"}. Frames never leave this machine."""
        data = request.get_json(silent=True) or {}
        if not data.get("image"):
            return jsonify(error="Missing 'image'"), 400
        img = decode_image(data)
        if img is None:
            return jsonify(error="Could not decode image"), 400
        try:
            return jsonify(rec.process_bgr(img))
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503

    @app.post("/api/collect")
    def collect():
        """Body: {"image", "label", "record": bool}. Saves one normalized sample when record is true."""
        data = request.get_json(silent=True) or {}
        label = data.get("label")
        if label not in WORDS:
            return jsonify(error="Unknown label"), 400
        img = decode_image(data)
        if img is None:
            return jsonify(error="Could not decode image"), 400
        try:
            points = rec.extract(img)
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503
        saved = False
        if points is not None and data.get("record"):
            dataset.append_sample(app.config["DATA_PATH"], label, normalize_landmarks(points))
            saved = True
        return jsonify(hand_detected=points is not None, landmarks=xy(points) if points else [],
                       saved=saved, label=label, count=dataset.counts(app.config["DATA_PATH"]).get(label, 0))

    @app.post("/api/reference")
    def save_reference():
        """Body: {"image", "label"}. Stores your own photo of the sign for the Learn/Train pages."""
        data = request.get_json(silent=True) or {}
        sign = next((x for x in SIGNS if x["word"] == data.get("label")), None)
        img = decode_image(data)
        if sign is None or img is None:
            return jsonify(error="Bad label or image"), 400
        folder = os.path.join(BASE, "static", "signs", "photos")
        os.makedirs(folder, exist_ok=True)
        cv2.imwrite(os.path.join(folder, sign["slug"] + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return jsonify(url=url_for("static", filename=f"signs/photos/{sign['slug']}.jpg") + f"?v={int(datetime.now().timestamp())}")

    @app.get("/api/tts")
    def tts():
        """Online voice fallback (Google TTS via gTTS) for languages the browser has no voice for.
        Only the sentence TEXT is sent to the internet - never camera frames."""
        lang = request.args.get("lang", "")
        text = (request.args.get("text") or "").strip()
        if lang not in {"en", "hi", "ta", "es", "fr"} or not text or len(text) > 300:
            return jsonify(error="Bad language or text"), 400
        try:
            from gtts import gTTS
            buf = io.BytesIO()
            gTTS(text=text, lang=lang).write_to_fp(buf)
        except ImportError:
            return jsonify(error='Install the online voice: python -m pip install gTTS'), 503
        except Exception as exc:  # no internet, blocked, etc.
            return jsonify(error="Online voice failed (internet needed): " + str(exc)), 503
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg")

    @app.post("/api/demo-video")
    def save_demo_video():
        """multipart: label + video. Stores your own short demo clip for the Learn page."""
        sign = next((x for x in SIGNS if x["word"] == request.form.get("label")), None)
        upload = request.files.get("video")
        if sign is None or upload is None:
            return jsonify(error="Bad label or video"), 400
        data = upload.read()
        if data[:4] == b"\x1aE\xdf\xa3":
            ext = "webm"
        elif data[4:8] == b"ftyp":
            ext = "mp4"
        else:
            return jsonify(error="Unsupported video format"), 400
        folder = os.path.join(BASE, "static", "signs", "videos")
        os.makedirs(folder, exist_ok=True)
        for old in ("webm", "mp4"):
            old_path = os.path.join(folder, f"{sign['slug']}.{old}")
            if os.path.exists(old_path):
                os.remove(old_path)
        with open(os.path.join(folder, f"{sign['slug']}.{ext}"), "wb") as f:
            f.write(data)
        return jsonify(url=url_for("static", filename=f"signs/videos/{sign['slug']}.{ext}") + f"?v={int(datetime.now().timestamp())}")

    @app.get("/api/dataset")
    def dataset_info():
        return jsonify(counts=dataset.counts(app.config["DATA_PATH"]))

    @app.delete("/api/dataset/<label>")
    def dataset_delete(label):
        return jsonify(removed=dataset.delete_label(app.config["DATA_PATH"], label))

    @app.post("/api/train")
    def train_model_api():
        from ml.train_model import train
        if not os.path.exists(app.config["DATA_PATH"]):
            return jsonify(error="No samples recorded yet."), 400
        try:
            report = train(app.config["DATA_PATH"], os.path.dirname(rec.model_path))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        rec.load_model()
        return jsonify(report)

    @app.get("/api/vocabulary")
    def vocabulary():
        return jsonify(signs=SIGNS, trained_classes=rec.classes)

    @app.get("/api/model-info")
    def model_info():
        return jsonify(model_loaded=rec.model is not None, threshold=rec.threshold, report=load_report())

    @app.get("/api/history")
    def get_history():
        rows = db().execute("SELECT * FROM history ORDER BY id DESC").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/api/history")
    def add_history():
        sentence = ((request.get_json(silent=True) or {}).get("sentence") or "").strip()
        if not sentence:
            return jsonify(error="Empty sentence"), 400
        conn = db()
        cur = conn.execute("INSERT INTO history (sentence, created_at) VALUES (?, ?)",
                           (sentence[:500], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return jsonify(id=cur.lastrowid), 201

    @app.delete("/api/history/<int:item_id>")
    def delete_one(item_id):
        conn = db()
        conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()
        return jsonify(ok=True)

    @app.delete("/api/history")
    def delete_all():
        conn = db()
        conn.execute("DELETE FROM history")
        conn.commit()
        return jsonify(ok=True)

    return app


if __name__ == "__main__":
    try:
        import mediapipe as _mp
        print("MediaPipe", _mp.__version__, "OK" if hasattr(_mp, "solutions") else "-> WRONG VERSION: " + fix_message(_mp.__version__))
    except ImportError:
        print("MediaPipe missing -> " + fix_message(None))
    create_app().run(host="127.0.0.1", port=5000, debug=False)
