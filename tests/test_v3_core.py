"""v3 core modules: behaviour is checked directly and for parity with the v2.8.0 implementations in main.py."""
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
import zipfile

import main
from geodesync.core import archive_safety, integrity, save_codec, versioning


class VersioningParity(unittest.TestCase):
    CASES = [("2.8.1", "2.8.0"), ("v2.9", "2.8.9"), ("2.8.0", "2.8.0"), ("2.7.9", "2.8.0"), ("", "2.8.0"),
             ("2.8.0-beta", "2.8.0"), ("3", "2.99.99"), (None, "1.0"), ("2.8.0.1", "2.8.0"), ("2.8", "2.8.0")]

    def test_matches_v2(self):
        for cand, cur in self.CASES:
            self.assertEqual(versioning.is_newer(cand, cur), main.is_newer_app_version(cand, cur), (cand, cur))
            self.assertEqual(versioning.sort_key(cand), main.version_sort_key(cand), cand)


class SaveCodec(unittest.TestCase):
    def test_round_trip_and_v2_compat(self):
        xml = b"<d><k>stars</k><i>1234</i></d>" * 50
        enc = save_codec.encode(xml)
        self.assertEqual(save_codec.decode(enc), xml)
        self.assertEqual(save_codec.decode(main.encode_geometry_dash_save(xml)), xml)
        self.assertEqual(main.decode_geometry_dash_save(enc), xml)


class Integrity(unittest.TestCase):
    def test_digest(self):
        data = b"payload"
        good = {"digest": "sha256:" + hashlib.sha256(data).hexdigest()}
        integrity.verify_release_asset_digest(good, data, "pkg")
        with self.assertRaises(ValueError):
            integrity.verify_release_asset_digest(good, b"tampered", "pkg")
        for bad in ({}, {"digest": "md5:abc"}, {"digest": "sha256:" + "z" * 64}):
            with self.assertRaises(ValueError):
                integrity.verify_release_asset_digest(bad, data, "pkg")

    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "cfg.json")
            integrity.atomic_write_json(p, {"a": 1})
            integrity.atomic_write_json(p, {"a": 2})
            self.assertEqual(json.load(open(p)), {"a": 2})
            self.assertEqual([f for f in os.listdir(os.path.dirname(p)) if f.startswith(".geodesync-write-")], [])


def make_zip(entries, symlink=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "target")
    buf.seek(0)
    return zipfile.ZipFile(buf)


class ArchiveSafety(unittest.TestCase):
    def test_rejects_unsafe_members(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("../evil.dll", "/abs.dll", "a/../../b", "CON.txt", "bad:name", "trail.", "x\\y"):
                with self.assertRaises(ValueError, msg=name):
                    archive_safety.validate_package(make_zip({name: b"x"}), d)
            with self.assertRaises(ValueError):
                archive_safety.validate_package(make_zip({"ok.dll": b"x"}, symlink="link"), d)
            with self.assertRaises(ValueError):
                archive_safety.validate_package(make_zip({}), d)

    def test_matches_v2_validation(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("../e", "fine/ok.dll", "NUL", "Geode.dll"):
                zf = make_zip({name: b"x"})
                try:
                    new = [t for _i, t in archive_safety.validate_package(zf, d)]
                except ValueError:
                    new = "error"
                try:
                    old = [t for _i, t in main.validate_geode_package_zip(zf, d)]
                except ValueError:
                    old = "error"
                self.assertEqual(new, old, name)

    def test_transactional_install_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "Geode.dll"), "wb").write(b"old")
            archive_safety.extract_transactionally(make_zip({"Geode.dll": b"new", "mods/a.geode": b"m"}), d)
            self.assertEqual(open(os.path.join(d, "Geode.dll"), "rb").read(), b"new")
            self.assertTrue(os.path.isfile(os.path.join(d, "mods", "a.geode")))
            os.makedirs(os.path.join(d, "blocked"))                      # a directory where the package wants a file
            with self.assertRaises(ValueError):
                archive_safety.extract_transactionally(make_zip({"Geode.dll": b"newer", "blocked": b"x"}), d)
            self.assertEqual(open(os.path.join(d, "Geode.dll"), "rb").read(), b"new")   # rolled back, nothing half-installed
            self.assertEqual([f for f in os.listdir(d) if f.startswith(".geodesync-geode-stage-")], [])

    def test_mod_ids(self):
        for ok in ("geode.loader", "user.cool-mod_2"):
            self.assertTrue(archive_safety.is_safe_mod_id(ok))
        for bad in ("../x.y", "nodot", "a.b.c", "", None, "a/b.c"):
            self.assertFalse(archive_safety.is_safe_mod_id(bad), bad)
            self.assertEqual(archive_safety.is_safe_mod_id(bad), main.is_safe_geode_mod_id(bad))


if __name__ == "__main__":
    unittest.main()
