import unittest
from fastapi.testclient import TestClient
from api.src.main import app

client = TestClient(app)

class TestAPIEndpoints(unittest.TestCase):
    def test_process_document(self):
        payload = {"text": "Sample document text containing PPA clauses."}
        response = client.post("/process", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("result", response.json())

if __name__ == '__main__':
    unittest.main()