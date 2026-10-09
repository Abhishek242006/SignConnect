import base64, os, tempfile, unittest
import cv2, numpy as np
from app import create_app
from signconnect.recognizer import Recognizer


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rec = Recognizer(model_path=os.path.join(self.tmp.name, "missing.joblib"))  # no model
        self.client = create_app(os.path.join(self.tmp.name, "t.db"), rec).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pages_load(self):
        for url in ["/", "/translator", "/history", "/learn", "/about"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_vocabulary(self):
        data = self.client.get("/api/vocabulary").get_json()
        self.assertEqual(len(data["signs"]), 17)
        self.assertEqual(data["trained_classes"], [])  # nothing claimed without a model

    def test_predict_validation(self):
        self.assertEqual(self.client.post("/api/predict", json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/predict", json={"image": "!!!"}).status_code, 400)

    def test_predict_blank_frame_no_hand(self):
        import mediapipe as mp
        if not hasattr(mp, "solutions"):
            self.skipTest("needs mediapipe==0.10.14 (solutions API)")
        ok, buf = cv2.imencode(".jpg", np.zeros((240, 320, 3), np.uint8))
        r = self.client.post("/api/predict", json={"image": base64.b64encode(buf).decode()})
        body = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertFalse(body["hand_detected"])
        self.assertFalse(body["model_loaded"])
        self.assertIsNone(body["word"])

    def test_history_crud(self):
        self.assertEqual(self.client.post("/api/history", json={"sentence": ""}).status_code, 400)
        new_id = self.client.post("/api/history", json={"sentence": "Hello."}).get_json()["id"]
        self.assertEqual(len(self.client.get("/api/history").get_json()), 1)
        self.client.delete(f"/api/history/{new_id}")
        self.assertEqual(self.client.get("/api/history").get_json(), [])
        self.client.post("/api/history", json={"sentence": "A"}); self.client.delete("/api/history")
        self.assertEqual(self.client.get("/api/history").get_json(), [])


if __name__ == "__main__":
    unittest.main()


class DatasetTests(unittest.TestCase):
    def test_collect_label_validation_and_dataset_roundtrip(self):
        from signconnect import dataset
        with tempfile.TemporaryDirectory() as d:
            csv = os.path.join(d, "l.csv")
            rec = Recognizer(model_path=os.path.join(d, "none.joblib"))
            client = create_app(os.path.join(d, "t.db"), rec, csv).test_client()
            self.assertEqual(client.post("/api/collect", json={"label": "Nope", "image": "x"}).status_code, 400)
            dataset.append_sample(csv, "Hello", [0.0] * 63)
            dataset.append_sample(csv, "Yes", [0.0] * 63)
            self.assertEqual(client.get("/api/dataset").get_json()["counts"], {"Hello": 1, "Yes": 1})
            self.assertEqual(client.delete("/api/dataset/Hello").get_json()["removed"], 1)
            self.assertEqual(client.get("/api/dataset").get_json()["counts"], {"Yes": 1})
            self.assertEqual(client.post("/api/train").status_code, 400)  # too few samples
            self.assertTrue(client.get("/api/status").get_json()["samples"] == {"Yes": 1})
            self.assertEqual(client.get("/train").status_code, 200)

    def test_sign_images_exist(self):
        from signconnect.vocabulary import SIGNS
        for s in SIGNS:
            self.assertTrue(os.path.exists(os.path.join("static", "signs", s["slug"] + ".svg")), s["slug"])


class ReferencePhotoTests(unittest.TestCase):
    def test_reference_photo_saved_and_removed(self):
        with tempfile.TemporaryDirectory() as d:
            client = create_app(os.path.join(d, "t.db"), Recognizer(model_path=os.path.join(d, "x"))).test_client()
            ok, buf = cv2.imencode(".jpg", np.full((60, 80, 3), 120, np.uint8))
            img = base64.b64encode(buf).decode()
            self.assertEqual(client.post("/api/reference", json={"image": img, "label": "Nope"}).status_code, 400)
            r = client.post("/api/reference", json={"image": img, "label": "Hello"})
            path = os.path.join("static", "signs", "photos", "hello.jpg")
            try:
                self.assertEqual(r.status_code, 200)
                self.assertTrue(os.path.exists(path))
                self.assertIn(b"photos/hello.jpg", client.get("/learn").data)
            finally:
                if os.path.exists(path):
                    os.remove(path)

    def test_status_reports_fix_when_mediapipe_unusable(self):
        with tempfile.TemporaryDirectory() as d:
            client = create_app(os.path.join(d, "t.db"), Recognizer(model_path=os.path.join(d, "x"))).test_client()
            st = client.get("/api/status").get_json()
            self.assertIn("mediapipe_ok", st)
            if not st["mediapipe_ok"]:
                self.assertIn("pip install mediapipe==0.10.14", st["fix"])


class VideoTests(unittest.TestCase):
    def test_learn_prefers_video_when_present(self):
        path = os.path.join("static", "signs", "videos", "hello.mp4")
        with tempfile.TemporaryDirectory() as d:
            client = create_app(os.path.join(d, "t.db"), Recognizer(model_path=os.path.join(d, "x"))).test_client()
            self.assertNotIn(b"videos/hello.mp4", client.get("/learn").data)
            open(path, "wb").write(b"\x00")
            try:
                self.assertIn(b"videos/hello.mp4", client.get("/learn").data)
            finally:
                os.remove(path)


class DemoVideoTests(unittest.TestCase):
    def test_demo_video_upload(self):
        import io
        path = os.path.join("static", "signs", "videos", "good.webm")
        with tempfile.TemporaryDirectory() as d:
            client = create_app(os.path.join(d, "t.db"), Recognizer(model_path=os.path.join(d, "x"))).test_client()
            bad = {"label": "Good", "video": (io.BytesIO(b"not a video"), "d")}
            self.assertEqual(client.post("/api/demo-video", data=bad, content_type="multipart/form-data").status_code, 400)
            good = {"label": "Good", "video": (io.BytesIO(b"\x1aE\xdf\xa3" + b"\x00" * 20), "d")}
            try:
                self.assertEqual(client.post("/api/demo-video", data=good, content_type="multipart/form-data").status_code, 200)
                self.assertIn(b"videos/good.webm", client.get("/learn").data)
            finally:
                if os.path.exists(path):
                    os.remove(path)


class TtsTests(unittest.TestCase):
    def test_tts_validation(self):
        with tempfile.TemporaryDirectory() as d:
            c = create_app(os.path.join(d, "t.db"), Recognizer(model_path=os.path.join(d, "x"))).test_client()
            self.assertEqual(c.get("/api/tts?lang=xx&text=hi").status_code, 400)
            self.assertEqual(c.get("/api/tts?lang=ta&text=").status_code, 400)
