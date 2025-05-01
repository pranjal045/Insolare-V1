import unittest
from data_pipeline.preprocessing import text_normalization

class TestTextNormalization(unittest.TestCase):
    def test_normalize_text(self):
        sample = "HEADER: Confidential\nDate: 12/31/2024\nAmount: $5000"
        normalized = text_normalization.normalize_text(sample)
        self.assertIn("date", normalized)
        self.assertIn("currency", normalized)

if __name__ == '__main__':
    unittest.main()