import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from triage import build_gemini_payload, build_response_schema


class TriageSchemaTests(unittest.TestCase):
    def test_build_response_schema_uses_plain_json_schema(self):
        schema = build_response_schema()

        self.assertEqual(schema.get("type"), "object")
        self.assertIn("properties", schema)
        self.assertIn("id", schema["properties"])
        self.assertIn("name", schema["properties"])
        self.assertEqual(schema["properties"]["name"]["type"], "string")

    def test_build_gemini_payload_uses_simple_schema(self):
        payload, generated_id, current_time = build_gemini_payload({"name": "Ana"})

        self.assertIn("contents", payload)
        self.assertIn("generationConfig", payload)
        self.assertIn("responseSchema", payload["generationConfig"])
        self.assertTrue(generated_id.startswith("PT-"))
        self.assertTrue(current_time)


if __name__ == "__main__":
    unittest.main()
