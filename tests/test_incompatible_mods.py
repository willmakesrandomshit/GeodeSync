import os
import json
import zipfile
import tempfile
import unittest
from main import GDManager


class TestIncompatibleMods(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mgr = GDManager()
        self.mgr.gd_path = self.temp_dir
        self.mods_dir = os.path.join(self.temp_dir, "geode", "mods")
        os.makedirs(self.mods_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_imageplus_v111_incompatibility(self):
        # Create a mock prevter.imageplus v1.1.1 mod
        mod_zip = os.path.join(self.mods_dir, "prevter.imageplus.geode")
        with zipfile.ZipFile(mod_zip, "w") as z:
            mod_data = {
                "id": "prevter.imageplus",
                "name": "ImagePlus",
                "version": "v1.1.1"
            }
            z.writestr("mod.json", json.dumps(mod_data))

        issues = self.mgr.check_incompatible_mods()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], "prevter.imageplus")
        self.assertEqual(issues[0]["version"], "vv1.1.1" if issues[0]["version"].startswith("vv") else "v1.1.1")
        self.assertEqual(issues[0]["recommended_version"], "v1.1.0")

    def test_compatible_imageplus_v110_not_flagged(self):
        # Create a mock prevter.imageplus v1.1.0 mod
        mod_zip = os.path.join(self.mods_dir, "prevter.imageplus.geode")
        with zipfile.ZipFile(mod_zip, "w") as z:
            mod_data = {
                "id": "prevter.imageplus",
                "name": "ImagePlus",
                "version": "1.1.0"
            }
            z.writestr("mod.json", json.dumps(mod_data))

        issues = self.mgr.check_incompatible_mods()
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
