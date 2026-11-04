import json
import os
import unittest
from unittest.mock import patch

from publisher.moderator import (
    _review_source_post,
    can_auto_publish,
    configured_model,
)


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class ModeratorTests(unittest.TestCase):
    def setUp(self):
        self.review = {
            "decision": "allow",
            "confidence": 0.97,
            "category": "news",
            "reason": "Relevant informational crypto news.",
            "flags": [],
        }

    def test_auto_publish_requires_high_confidence_informational_content(self):
        self.assertTrue(can_auto_publish(self.review))
        self.assertFalse(can_auto_publish({**self.review, "confidence": 0.89}))
        self.assertFalse(can_auto_publish({**self.review, "category": "promotion"}))
        self.assertFalse(can_auto_publish({**self.review, "flags": ["unverified_claim"]}))
        self.assertFalse(can_auto_publish({**self.review, "decision": "hold"}))
        self.assertFalse(can_auto_publish({**self.review, "confidence": True}))

    def test_model_can_be_configured_without_changing_code(self):
        with patch.dict(os.environ, {"CRYPTOPING_MODERATOR_MODEL": "gpt-6-luna"}):
            self.assertEqual(configured_model(), "gpt-6-luna")

    def test_responses_api_json_is_parsed_and_request_is_bounded(self):
        model_output = json.dumps(self.review)
        payload = {
            "output": [{
                "content": [{"type": "output_text", "text": model_output}]
            }]
        }
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "CRYPTOPING_MODERATOR_TIMEOUT_SECONDS": "12",
            "CRYPTOPING_MODERATOR_MODEL": "gpt-6-luna",
        }):
            with patch("publisher.moderator.urllib.request.urlopen", return_value=FakeHTTPResponse(payload)) as call:
                result = _review_source_post("Bitcoin update", "Bitcoin hash rate reached a monthly high.")
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["confidence"], 0.97)
        self.assertEqual(result["provider"], "openai")
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request_body["model"], "gpt-6-luna")
        self.assertEqual(request_body["max_output_tokens"], 160)
        self.assertEqual(request_body["text"]["format"]["type"], "json_schema")
        self.assertEqual(call.call_args.kwargs["timeout"], 12)

    def test_missing_api_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "openai_api_key_not_configured"):
                _review_source_post("Title", "Body")

    def test_invalid_model_output_fails_closed(self):
        payload = {
            "output": [{
                "content": [{"type": "output_text", "text": '{"decision":"allow","confidence":"high"}'}]
            }]
        }
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("publisher.moderator.urllib.request.urlopen", return_value=FakeHTTPResponse(payload)):
                with self.assertRaisesRegex(RuntimeError, "moderator_invalid_confidence"):
                    _review_source_post("Title", "Body")

    def test_refusal_fails_closed(self):
        payload = {
            "output": [{
                "content": [{"type": "refusal", "refusal": "Cannot review"}]
            }]
        }
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("publisher.moderator.urllib.request.urlopen", return_value=FakeHTTPResponse(payload)):
                with self.assertRaisesRegex(RuntimeError, "model_refusal"):
                    _review_source_post("Title", "Body")


if __name__ == "__main__":
    unittest.main()

[executed on device: Gensyn2.play2go.cloud (03201713-0ab1-4309-bc64-9b0566307ce7)]