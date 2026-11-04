import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wplay.file_manager.file_manager import FileManager


class FileManagerCredentialTests(unittest.TestCase):
    def test_environment_pair_takes_priority_over_local_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "credentials.json"
            local_file.write_text(
                json.dumps({"username": "local-user", "password": "local-pass"}),
                encoding="utf-8",
            )
            environment = {
                "WPLAY_USERNAME": "environment-user",
                "WPLAY_PASSWORD": "environment-pass",
            }
            with patch.dict(os.environ, environment, clear=True):
                self.assertEqual(
                    FileManager.load_credentials(str(local_file)),
                    ("environment-user", "environment-pass"),
                )

    def test_partial_environment_pair_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "credentials.json"
            local_file.write_text(
                json.dumps({"username": "local-user", "password": "local-pass"}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"WPLAY_USERNAME": "environment-user"}, clear=True):
                self.assertEqual(
                    FileManager.load_credentials(str(local_file)),
                    (None, None),
                )

    def test_ignored_local_file_remains_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "credentials.json"
            local_file.write_text(
                json.dumps({"username": "local-user", "password": "local-pass"}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    FileManager.load_credentials(str(local_file)),
                    ("local-user", "local-pass"),
                )

    def test_missing_file_returns_none_pair(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_file = Path(temp_dir) / "missing.json"
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    FileManager.load_credentials(str(missing_file)),
                    (None, None),
                )

    def test_malformed_local_file_returns_none_pair(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bad_file = Path(temp_dir) / "credentials.json"
            bad_file.write_text("{not-json", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    FileManager.load_credentials(str(bad_file)),
                    (None, None),
                )


if __name__ == "__main__":
    unittest.main()
