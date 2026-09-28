"""Offline privacy/configuration regression checks; no external services."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from demo_config import DemoConfigurationError, validate_ollama_url
import release_guard
import deploy


class PrivateConfigurationTests(unittest.TestCase):
    def test_requires_explicit_usable_service_origin(self):
        for value in ("", "http://ollama.example.invalid:11434", "file:///tmp/model",
                      "http://user:password@model:11434", "http://model:bad",
                      "http://model:11434/path", "http://model:11434?token=x",
                      "http://model:11434\nINJECT=value"):
            with self.subTest(value=value), self.assertRaises(DemoConfigurationError):
                validate_ollama_url(value)
        self.assertEqual(validate_ollama_url("http://model-service:11434"),
                         "http://model-service:11434")

    def test_private_host_identity_is_required_and_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory).resolve() / "runtime.env"
            with patch.object(release_guard, "RUNTIME", runtime), patch.object(
                    release_guard.socket, "gethostname", return_value="approved-demo"):
                with self.assertRaises(RuntimeError):
                    release_guard.require_deployment_host()
                (runtime.parent / "hostname").write_text("wrong-host")
                with self.assertRaises(RuntimeError):
                    release_guard.require_deployment_host()
                (runtime.parent / "hostname").write_text("approved-demo\n")
                release_guard.require_deployment_host()

    def test_remote_staging_uses_remote_home_and_validated_archive(self):
        import shlex
        with patch.object(deploy.subprocess, "run") as run:
            deploy.stage(b"archive", "a" * 16)
        command = run.call_args.args[0][-1]
        source = shlex.split(command)[2]
        self.assertIn("pathlib.Path.home()", source)
        self.assertIn("assert set(files)==expected", source)
        self.assertIn("marker.is_file()", source)
        compile(source, "remote-stage", "exec")


if __name__ == "__main__":
    unittest.main()
