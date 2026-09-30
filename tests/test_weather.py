import unittest
from datetime import datetime
from weather import classify, due, LABELS

class WeatherTests(unittest.TestCase):
    def test_boundaries(self):
        for value, label in [(-2.01, 0), (-2, 1), (-1.01, 1), (-1, 2), (1, 2), (1.01, 3), (2, 3), (2.01, 4)]:
            self.assertEqual(classify(value, 0, 1), LABELS[label])
    def test_shared_baseline(self):
        self.assertEqual([classify(v, 15, 5) for v in [15, 22, 4]], [LABELS[2], LABELS[3], LABELS[0]])
    def test_wake_and_deduplication(self):
        self.assertFalse(due(datetime(2026, 9, 30, 6, 59), None))
        self.assertTrue(due(datetime(2026, 9, 30, 10), '2026-09-29'))
        self.assertFalse(due(datetime(2026, 9, 30, 10), '2026-09-30'))
