"""v3 architecture rules, enforced: the core, platform and services layers never depend on the UI."""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "geodesync"
LOGIC_DIRS = ("core", "platform", "services")


def _logic_modules():
    for d in LOGIC_DIRS:
        for path in sorted((PKG / d).rglob("*.py")):
            yield path


class ArchitectureTests(unittest.TestCase):
    def test_logic_layers_do_not_import_tk_or_ui(self):
        for path in _logic_modules():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    with self.subTest(module=str(path.relative_to(ROOT)), imports=name):
                        self.assertFalse(name == "tkinter" or name.startswith("tkinter.") or name.startswith("geodesync.ui"))

    def test_every_logic_module_imports_without_tkinter(self):
        modules = [".".join(p.relative_to(ROOT).with_suffix("").parts) for p in _logic_modules() if p.name != "__init__.py"]
        code = (
            "import builtins, importlib, sys\n"
            "real = builtins.__import__\n"
            "def guard(name, *a, **k):\n"
            "    if name == 'tkinter' or name.startswith('tkinter.'): raise ImportError('tkinter blocked')\n"
            "    return real(name, *a, **k)\n"
            "builtins.__import__ = guard\n"
            f"for m in {modules!r}: importlib.import_module(m)\n"
            "print('ok')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-800:])

    def test_main_is_a_small_launcher(self):
        self.assertLess(len((ROOT / "main.py").read_text(encoding="utf-8").splitlines()), 300)

    def test_gdmanager_is_composed_from_the_six_domain_mixins(self):
        from geodesync.services.gd.manager import GDManager
        names = [c.__name__ for c in GDManager.__mro__]
        for mixin in ("SteamMixin", "GameMixin", "ModsMixin", "AssetsMixin", "SavesMixin", "DemonlistMixin"):
            self.assertIn(mixin, names)

    def test_pyw_launcher_has_no_logic_copy(self):
        self.assertLess(len((ROOT / "GeodeSync.pyw").read_text(encoding="utf-8").splitlines()), 40)


if __name__ == "__main__":
    unittest.main()
