"""Run with: python3 -m unittest discover -s tests"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


EXPORTER = Path(__file__).resolve().parents[1] / "bin" / "keybinds"


class DefaultBrowserTests(unittest.TestCase):
    def export(self, helper=None, xdg="omarchy-browser.desktop", mime="chromium.desktop"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = {
                "omarchy-menu-keybindings":
                    "output_binding_records() { :; }\noutput_keybindings() {\n",
                "xdg-settings": "printf '%s\\n' '" + xdg + "'\n",
                "xdg-mime": "printf '%s\\n' '" + mime + "'\n",
            }
            if helper is not None:
                scripts["omarchy-cmd-default-browser"] = helper
            # Isolate command discovery from the host's installed Omarchy helper.
            for name in ("bash", "sed", "jq", "env"):
                (root / name).symlink_to(shutil.which(name))
            for name, content in scripts.items():
                script = root / name
                script.write_text("#!/bin/bash\n" + content)
                script.chmod(0o755)
            env = dict(os.environ, PATH=str(root), HOME=str(root))
            result = subprocess.run(
                ["/bin/bash", str(EXPORTER)], env=env,
                capture_output=True, text=True, check=True,
            )
            return json.loads(result.stdout)["defaults"]["browser"]

    def test_omarchy_resolver_takes_precedence_over_routing_entry(self):
        self.assertEqual(self.export("echo firefox.desktop\n"), "firefox")

    def test_older_omarchy_without_helper_uses_xdg_settings(self):
        self.assertEqual(self.export(xdg="firefox.desktop"), "firefox")

    def test_empty_resolver_uses_xdg_settings(self):
        self.assertEqual(self.export(":\n", xdg="firefox.desktop"), "firefox")

    def test_failed_resolver_uses_xdg_settings(self):
        self.assertEqual(self.export("exit 1\n", xdg="firefox.desktop"), "firefox")

    def test_empty_xdg_settings_uses_mime_fallback(self):
        self.assertEqual(self.export(xdg=""), "chromium")
