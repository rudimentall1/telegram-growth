import unittest
from unittest.mock import patch

from scripts import submit_directory


def listed():
    return {"content": [{"type": "text", "text": "Channel cryptoping_ru: https://t.me/cryptoping_ru"}]}


def missing():
    return {"content": [{"type": "text", "text": "Resource not found"}]}


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def initialize(self):
        self.calls.append(("initialize", None))

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class DirectorySubmissionTests(unittest.TestCase):
    def test_existing_listing_is_idempotent(self):
        client = FakeClient([listed()])
        with patch.object(submit_directory, "MCPClient", return_value=client):
            self.assertEqual(submit_directory.main(), 0)
        self.assertEqual([call[0] for call in client.calls], ["initialize", "get_resource"])

    def test_submits_then_verifies_listing(self):
        client = FakeClient([missing(), {"content": [{"text": "Submission accepted"}]}, listed()])
        with patch.object(submit_directory, "MCPClient", return_value=client):
            self.assertEqual(submit_directory.main(), 0)
        self.assertEqual(
            [call[0] for call in client.calls],
            ["initialize", "get_resource", "submit_listing", "get_resource"],
        )
        self.assertEqual(
            client.calls[2][1],
            {"handle": submit_directory.HANDLE, "type": "channel"},
        )

    def test_does_not_claim_success_without_lookup_confirmation(self):
        client = FakeClient([missing(), {"content": [{"text": "Submission accepted"}]}, missing()])
        with patch.object(submit_directory, "MCPClient", return_value=client):
            self.assertEqual(submit_directory.main(), 1)

    def test_mcp_failure_returns_nonzero(self):
        client = FakeClient([submit_directory.MCPError("directory unavailable")])
        with patch.object(submit_directory, "MCPClient", return_value=client):
            self.assertEqual(submit_directory.main(), 1)


if __name__ == "__main__":
    unittest.main()
