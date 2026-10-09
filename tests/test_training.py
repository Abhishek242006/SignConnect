import json, os, tempfile, unittest
import joblib
from ml.generate_demo_data import generate
from ml.train_model import train
from signconnect.features import NUM_FEATURES
from signconnect.vocabulary import WORDS


class TrainingTests(unittest.TestCase):
    def test_pipeline_on_synthetic_data(self):
        with tempfile.TemporaryDirectory() as d:
            csv = generate(os.path.join(d, "demo.csv"), per_class=40)
            report = train(csv, d)
            self.assertEqual(sorted(report["classes"]), sorted(WORDS))
            self.assertIn(report["best_model"], report["models"])
            self.assertGreater(report["models"][report["best_model"]]["accuracy"], 0.9)
            model = joblib.load(os.path.join(d, "gesture_model.joblib"))
            self.assertEqual(model.predict_proba([[0.0] * NUM_FEATURES]).shape[1], len(WORDS))
            self.assertTrue(os.path.exists(os.path.join(d, "confusion_matrix.png")))

    def test_too_few_samples_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            csv = generate(os.path.join(d, "tiny.csv"), per_class=3)
            with self.assertRaises(ValueError):
                train(csv, d)


if __name__ == "__main__":
    unittest.main()
