import unittest
from model_training.scripts.finetune_llm import load_configs

class TestModelInference(unittest.TestCase):
    def test_load_configs(self):
        base_config, training_params = load_configs()
        self.assertIn("model_name", base_config)
        self.assertIn("epochs", training_params)

if __name__ == '__main__':
    unittest.main()