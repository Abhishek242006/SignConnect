import unittest
import numpy as np
from signconnect.features import normalize_landmarks, NUM_FEATURES


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.pts = np.random.default_rng(1).random((21, 3))

    def test_length(self):
        self.assertEqual(len(normalize_landmarks(self.pts)), NUM_FEATURES)

    def test_wrist_is_origin(self):
        self.assertTrue(np.allclose(normalize_landmarks(self.pts)[:3], 0))

    def test_translation_and_scale_invariant(self):
        a = normalize_landmarks(self.pts)
        moved = self.pts * 2.5 + np.array([0.3, -0.2, 0.0])
        moved[:, 2] = self.pts[:, 2] * 2.5  # z scaled only
        self.assertTrue(np.allclose(a, normalize_landmarks(moved), atol=1e-5))


if __name__ == "__main__":
    unittest.main()
