"""Additional tests for chunking behavior."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chuncking import split_text_into_chunks


class ChunkingBehaviorTests(unittest.TestCase):
    def test_short_document_produces_one_chunk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short.txt"
            path.write_text("A short note.", encoding="utf-8")

            chunks = split_text_into_chunks(str(path))

            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0]["text"], "A short note.")
            self.assertEqual(chunks[0]["chunk_index"], 0)

    def test_chunking_delegates_loading_to_universal_loader(self):
        with patch("chuncking.universal_file_loader", return_value="loaded content") as loader:
            chunks = split_text_into_chunks("document.txt")

            loader.assert_called_once_with("document.txt")
            self.assertEqual(chunks[0]["text"], "loaded content")


if __name__ == "__main__":
    unittest.main()
