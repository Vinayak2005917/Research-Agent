"""Smoke tests for the static frontend files."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class FrontendAssetTests(unittest.TestCase):
    def test_setup_page_contains_upload_and_start_controls(self):
        html = (FRONTEND / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="username"', html)
        self.assertIn('id="fileInput"', html)
        self.assertIn('id="startBtn"', html)
        self.assertIn("index.js", html)

    def test_chat_page_contains_message_form_and_file_controls(self):
        html = (FRONTEND / "chat.html").read_text(encoding="utf-8")

        self.assertIn('id="chat"', html)
        self.assertIn('id="input"', html)
        self.assertIn('id="filesBtn"', html)
        self.assertIn('id="chatFileInput"', html)
        self.assertIn("chat.js", html)

    def test_chat_script_handles_websocket_responses_and_uploads(self):
        javascript = (FRONTEND / "chat.js").read_text(encoding="utf-8")

        self.assertIn("new WebSocket", javascript)
        self.assertIn('msg.type === "response"', javascript)
        self.assertIn("/upload", javascript)
        self.assertIn("renderMarkdown", javascript)


if __name__ == "__main__":
    unittest.main()
