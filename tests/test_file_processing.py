"""Tests for document loading and text chunking."""

import json
import tempfile
import unittest
from pathlib import Path

from chuncking import split_text_into_chunks
from file_loaders import universal_file_loader


class FileProcessingTests(unittest.TestCase):
    def test_loads_json_as_pretty_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.json"
            path.write_text(json.dumps({"title": "Research", "year": 2026}), encoding="utf-8")

            loaded = universal_file_loader(str(path))

            self.assertIn('"title": "Research"', loaded)
            self.assertIn('"year": 2026', loaded)

    def test_loads_plain_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.txt"
            expected = "A short research note."
            path.write_text(expected, encoding="utf-8")

            self.assertEqual(universal_file_loader(str(path)), expected)

    def test_rejects_unsupported_file_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.exe"
            path.write_bytes(b"not a supported document")

            with self.assertRaises(ValueError):
                universal_file_loader(str(path))

    def test_chunks_include_source_and_sequential_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "long.txt"
            path.write_text("research " * 200, encoding="utf-8")

            chunks = split_text_into_chunks(str(path))

            self.assertGreater(len(chunks), 1)
            self.assertEqual([chunk["chunk_index"] for chunk in chunks], list(range(len(chunks))))
            self.assertTrue(all(chunk["source"] == str(path) for chunk in chunks))
            self.assertTrue(all(chunk["text"] for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
