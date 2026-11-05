import json
import os
import unittest
import urllib.error
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
        self.model_text = json.dumps(self.review)

    def gemini_payload(self, text=None):
        return {
            "candidates": [{
                "content": {
                    "parts": [{"text": text or self.model_text}],
                },
            }],
        }

    def groq_payload(self, text=None):
        return {
            "choices": [{
                "message": {"content": text or self.model_text},
            }],
        }

    def test_auto_publish_requires_high_confidence_informational_content(self):
        self.assertTrue(can_auto_publish(self.review))
        self.assertFalse(can_auto_publish({**self.review, "confidence": 0.89}))
        self.assertFalse(can_auto_publish({**self.review, "category": "promotion"}))
        self.assertFalse(can_auto_publish({**self.review, "flags": ["unverified_claim"]}))
        self.assertFalse(can_auto_publish({**self.review, "decision": "hold"}))
        self.assertFalse(can_auto_publish({**self.review, "confidence": True}))

    def test_provider_models_have_safe_defaults_and_openai_legacy_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_model("gemini"), "gemini-3.1-flash-lite")
            self.assertEqual(configured_model("groq"), "openai/gpt-oss-20b")
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_MODEL": "custom-openai-model",
        }, clear=True):
            self.assertEqual(configured_model("openai"), "custom-openai-model")

    def test_gemini_generate_content_json_response(self):
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-test-key",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                return_value=FakeHTTPResponse(self.gemini_payload()),
            ) as call:
                result = _review_source_post("Bitcoin update", "Hash rate reached a monthly high.")

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "gemini-3.1-flash-lite")
        request = call.call_args.args[0]
        self.assertIn("/models/gemini-3.1-flash-lite:generateContent", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-test-key")
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request_body["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("responseJsonSchema", request_body["generationConfig"])
        self.assertEqual(call.call_args.kwargs["timeout"], 30)

    def test_groq_chat_completions_json_schema(self):
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "groq",
            "GROQ_API_KEY": "groq-test-key",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                return_value=FakeHTTPResponse(self.groq_payload()),
            ) as call:
                result = _review_source_post("Bitcoin update", "Hash rate reached a monthly high.")

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["provider"], "groq")
        self.assertEqual(result["model"], "openai/gpt-oss-20b")
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer groq-test-key")
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request_body["response_format"]["type"], "json_schema")
        self.assertTrue(request_body["response_format"]["json_schema"]["strict"])

    def test_gemini_failure_falls_back_to_groq(self):
        http_error = urllib.error.HTTPError(
            "https://example.invalid", 503, "unavailable", {}, None,
        )
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-test-key",
            "GROQ_API_KEY": "groq-test-key",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                side_effect=[http_error, FakeHTTPResponse(self.groq_payload())],
            ) as call:
                result = _review_source_post("Title", "Body")

        self.assertEqual(call.call_count, 2)
        self.assertEqual(result["provider"], "groq")
        self.assertTrue(can_auto_publish(result))

    def test_openai_remains_available_as_explicit_alternative(self):
        openai_payload = {
            "output": [{
                "content": [{"type": "output_text", "text": self.model_text}],
            }],
        }
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "openai",
            "OPENAI_API_KEY": "openai-test-key",
            "CRYPTOPING_MODERATOR_MODEL": "gpt-6-luna",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                return_value=FakeHTTPResponse(openai_payload),
            ) as call:
                result = _review_source_post("Title", "Body")

        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["model"], "gpt-6-luna")
        self.assertEqual(
            call.call_args.args[0].full_url,
            "https://api.openai.com/v1/responses",
        )

    def test_missing_provider_keys_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "moderator_no_provider_api_key_configured",
            ):
                _review_source_post("Title", "Body")

    def test_invalid_json_fails_closed_without_publishing(self):
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-test-key",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                return_value=FakeHTTPResponse(self.gemini_payload("{invalid")),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "moderator_all_providers_failed",
                ):
                    _review_source_post("Title", "Body")

    def test_invalid_result_shape_fails_closed(self):
        payload = self.gemini_payload(json.dumps({
            "decision": "allow",
            "confidence": "high",
        }))
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-test-key",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                return_value=FakeHTTPResponse(payload),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "moderator_all_providers_failed",
                ):
                    _review_source_post("Title", "Body")

    def test_http_errors_fail_closed_after_all_configured_providers(self):
        error = urllib.error.HTTPError(
            "https://example.invalid", 429, "rate limited", {}, None,
        )
        with patch.dict(os.environ, {
            "CRYPTOPING_MODERATOR_PROVIDER": "gemini",
            "GEMINI_API_KEY": "gemini-test-key",
            "GROQ_API_KEY": "groq-test-key",
        }, clear=True):
            with patch(
                "publisher.moderator.urllib.request.urlopen",
                side_effect=[error, error],
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "moderator_all_providers_failed",
                ):
                    _review_source_post("Title", "Body")


if __name__ == "__main__":
    unittest.main()

