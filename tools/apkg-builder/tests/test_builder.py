from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


BUILDER_ROOT = Path(__file__).resolve().parents[1]
BUILD_CLI = BUILDER_ROOT / "build_apkg.py"
VERIFY_CLI = BUILDER_ROOT / "verify_apkg.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BuilderCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "front.html").write_text("<div>{{Text}}</div>\n", encoding="utf-8")
        (self.source / "back.html").write_text("{{FrontSide}}<hr>{{Text}}\n", encoding="utf-8")
        (self.source / "styling.css").write_text(".card { color: black; }\n", encoding="utf-8")
        self.manifest_path = self.source / "deck.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_manifest(self, data: dict) -> Path:
        self.manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return self.manifest_path

    def minimal_manifest(self) -> dict:
        return {
            "schema_version": 1,
            "name": "Example",
            "deck": {"id": 1000, "name": "Example", "mod": 1700000000, "usn": -1},
            "notetype": {
                "id": 2000,
                "name": "Basic",
                "kind": 0,
                "sort_field": 0,
                "fields": [
                    {
                        "name": "Text",
                        "ord": 0,
                        "font": "Arial",
                        "size": 20,
                        "sticky": False,
                    }
                ],
                "templates": [
                    {
                        "name": "Card 1",
                        "ord": 0,
                        "front_file": "front.html",
                        "front_hash": sha256(self.source / "front.html"),
                        "back_file": "back.html",
                        "back_hash": sha256(self.source / "back.html"),
                    }
                ],
                "requirements": [[0, "any", [0]]],
                "css_file": "styling.css",
                "css_hash": sha256(self.source / "styling.css"),
            },
            "notes": [
                {
                    "id": 3000,
                    "guid": "example-guid",
                    "mod": 1700000001,
                    "usn": -1,
                    "tags": [],
                    "raw_tags": "",
                    "fields": ["hello"],
                    "sort_field": "hello",
                    "flags": 0,
                    "data": "",
                    "cards": [
                        {
                            "id": 4000,
                            "did": 1000,
                            "ord": 0,
                            "mod": 1700000001,
                            "usn": -1,
                            "type": 0,
                            "queue": 0,
                            "due": 1,
                            "ivl": 0,
                            "factor": 0,
                            "reps": 0,
                            "lapses": 0,
                            "left": 0,
                            "odue": 0,
                            "odid": 0,
                            "flags": 0,
                            "data": "{}",
                        }
                    ],
                }
            ],
            "media": [],
        }

    def run_cli(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_build_is_deterministic(self) -> None:
        manifest = self.write_manifest(self.minimal_manifest())
        first = self.root / "first.apkg"
        second = self.root / "second.apkg"

        first_result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(first),
        )
        second_result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(second),
        )

        self.assertEqual(first_result.returncode, 0, first_result.stderr)
        self.assertEqual(second_result.returncode, 0, second_result.stderr)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_verify_accepts_a_package_built_from_the_manifest(self) -> None:
        manifest = self.write_manifest(self.minimal_manifest())
        package = self.root / "example.apkg"
        build_result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(package),
        )
        self.assertEqual(build_result.returncode, 0, build_result.stderr)

        verify_result = self.run_cli(
            VERIFY_CLI,
            "verify",
            "--manifest",
            str(manifest),
            "--package",
            str(package),
        )

        self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
        self.assertIn("Verified", verify_result.stdout)

    def test_verifier_enforces_explicit_ids_and_card_requirements(self) -> None:
        manifest_data = self.minimal_manifest()
        manifest = self.write_manifest(manifest_data)
        package = self.root / "example.apkg"
        build_result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(package),
        )
        self.assertEqual(build_result.returncode, 0, build_result.stderr)

        manifest_data["notes"][0]["id"] = 9999
        self.write_manifest(manifest_data)
        id_result = self.run_cli(
            VERIFY_CLI,
            "verify",
            "--manifest",
            str(manifest),
            "--package",
            str(package),
        )
        self.assertNotEqual(id_result.returncode, 0)
        self.assertIn("note ID differs", id_result.stderr)

        manifest_data = self.minimal_manifest()
        manifest_data["notetype"]["requirements"] = [[0, "none", [0]]]
        self.write_manifest(manifest_data)
        requirement_result = self.run_cli(
            VERIFY_CLI,
            "verify",
            "--manifest",
            str(manifest),
            "--package",
            str(package),
        )
        self.assertNotEqual(requirement_result.returncode, 0)
        self.assertIn("card requirements differ", requirement_result.stderr)

    def test_media_uses_manifest_indexes_and_order(self) -> None:
        media_dir = self.source / "media"
        media_dir.mkdir()
        (media_dir / "first.bin").write_bytes(b"first")
        (media_dir / "second.bin").write_bytes(b"second")
        manifest_data = self.minimal_manifest()
        manifest_data["media"] = [
            {
                "index": 1,
                "name": "second.bin",
                "file": "media/second.bin",
                "size": 6,
                "sha256": sha256(media_dir / "second.bin"),
            },
            {
                "index": 0,
                "name": "first.bin",
                "file": "media/first.bin",
                "size": 5,
                "sha256": sha256(media_dir / "first.bin"),
            },
        ]
        manifest = self.write_manifest(manifest_data)
        package = self.root / "media.apkg"
        build_result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(package),
        )
        self.assertEqual(build_result.returncode, 0, build_result.stderr)

        with zipfile.ZipFile(package) as archive:
            self.assertEqual(
                archive.namelist(),
                ["collection.anki2", "0", "1", "media"],
            )
            self.assertEqual(archive.read("0"), b"first")
            self.assertEqual(archive.read("1"), b"second")
            self.assertEqual(
                json.loads(archive.read("media")),
                {"0": "first.bin", "1": "second.bin"},
            )

    def test_build_rejects_a_changed_hashed_source(self) -> None:
        manifest = self.write_manifest(self.minimal_manifest())
        (self.source / "styling.css").write_text(".card { color: red; }\n", encoding="utf-8")
        package = self.root / "invalid.apkg"

        result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(package),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)
        self.assertFalse(package.exists())

    def test_build_rejects_duplicate_ids_guids_and_media_entries(self) -> None:
        cases = [
            ("note id", "duplicate note id"),
            ("note guid", "duplicate note GUID"),
            ("card id", "duplicate card id"),
            ("media index", "duplicate media index"),
            ("media name", "duplicate media name"),
        ]
        for label, expected_error in cases:
            with self.subTest(label=label):
                manifest_data = self.minimal_manifest()
                if label == "note id":
                    manifest_data["notes"].append(dict(manifest_data["notes"][0]))
                elif label == "note guid":
                    duplicate = dict(manifest_data["notes"][0])
                    duplicate["id"] = 3001
                    manifest_data["notes"].append(duplicate)
                elif label == "card id":
                    second_note = dict(manifest_data["notes"][0])
                    second_note["id"] = 3001
                    second_note["guid"] = "another-guid"
                    second_note["cards"] = [dict(manifest_data["notes"][0]["cards"][0])]
                    manifest_data["notes"].append(second_note)
                else:
                    media_dir = self.source / "media"
                    media_dir.mkdir(exist_ok=True)
                    (media_dir / "item.bin").write_bytes(b"item")
                    item = {
                        "index": 0,
                        "name": "item.bin",
                        "file": "media/item.bin",
                        "size": 4,
                        "sha256": sha256(media_dir / "item.bin"),
                    }
                    if label == "media index":
                        duplicate = dict(item)
                        duplicate["name"] = "other.bin"
                        duplicate["file"] = "media/item.bin"
                        manifest_data["media"] = [item, duplicate]
                    else:
                        duplicate = dict(item)
                        duplicate["index"] = 1
                        manifest_data["media"] = [item, duplicate]

                manifest = self.write_manifest(manifest_data)
                package = self.root / f"{label.replace(' ', '-')}.apkg"
                result = self.run_cli(
                    BUILD_CLI,
                    "build",
                    "--manifest",
                    str(manifest),
                    "--out",
                    str(package),
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)
                self.assertFalse(package.exists())

    def test_build_requires_hashes_for_every_template_and_css_source(self) -> None:
        manifest_data = self.minimal_manifest()
        del manifest_data["notetype"]["templates"][0]["front_hash"]
        manifest = self.write_manifest(manifest_data)
        package = self.root / "missing-hash.apkg"

        result = self.run_cli(
            BUILD_CLI,
            "build",
            "--manifest",
            str(manifest),
            "--out",
            str(package),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("front_hash must be a non-empty string", result.stderr)
        self.assertFalse(package.exists())


if __name__ == "__main__":
    unittest.main()
