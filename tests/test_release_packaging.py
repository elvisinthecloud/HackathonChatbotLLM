"""New local backend modules must survive the explicit deployment/build allowlists."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_guard import ALLOWLIST


class ReleasePackagingTests(unittest.TestCase):
    def test_backend_modules_are_in_both_release_and_docker_allowlists(self):
        patterns = (ROOT / 'backend/.dockerignore').read_text().splitlines()
        self.assertIn('**', patterns)
        for module in (ROOT / 'backend').glob('*.py'):
            with self.subTest(module=module.name):
                self.assertIn('backend/' + module.name, ALLOWLIST)
                self.assertIn('!' + module.name, patterns)
