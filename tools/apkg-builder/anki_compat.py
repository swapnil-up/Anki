#!/usr/bin/env python3
"""Check that a rebuilt APKG imports into Anki with the expected content.

Run this script with Anki's bundled Python and its app_packages directory on
PYTHONPATH. It creates a temporary collection and never opens the user's live
Anki profile.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from anki.collection import Collection, ImportAnkiPackageRequest
except ImportError as exc:  # pragma: no cover - depends on Anki installation
    raise SystemExit(
        "Run this script with Anki's bundled Python and PYTHONPATH set to "
        "Anki's app_packages directory."
    ) from exc

from anki_build.manifest import LoadedManifest, load_manifest, safe_source_path


class CompatibilityError(ValueError):
    """Raised when Anki changes the package's expected logical content."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CompatibilityError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_model(manifest: LoadedManifest, model: dict[str, Any]) -> None:
    expected = manifest.notetype
    allowed_names = {expected["name"], f"{expected['name']}+"}
    require(model.get("name") in allowed_names, "imported note type name differs")
    require(model.get("req") == expected["requirements"], "imported card requirements differ")

    css_path = safe_source_path(manifest.base_dir, expected["css_file"], "CSS")
    require(model.get("css") == css_path.read_text(encoding="utf-8"), "imported CSS differs")

    fields = model.get("flds", [])
    require(len(fields) == len(expected["fields"]), "imported field count differs")
    for imported, source in zip(
        sorted(fields, key=lambda item: item["ord"]),
        sorted(expected["fields"], key=lambda item: item["ord"]),
    ):
        require(imported.get("name") == source["name"], "imported field name differs")
        require(imported.get("ord") == source["ord"], "imported field order differs")
        require(imported.get("font") == source.get("font", "Arial"), "imported field font differs")
        require(imported.get("size") == source.get("size", 20), "imported field size differs")

    templates = model.get("tmpls", [])
    require(len(templates) == len(expected["templates"]), "imported template count differs")
    for imported, source in zip(
        sorted(templates, key=lambda item: item["ord"]),
        sorted(expected["templates"], key=lambda item: item["ord"]),
    ):
        require(imported.get("name") == source["name"], "imported template name differs")
        require(imported.get("ord") == source["ord"], "imported template order differs")
        front = safe_source_path(
            manifest.base_dir, source["front_file"], "template front"
        ).read_text(encoding="utf-8")
        back = safe_source_path(
            manifest.base_dir, source["back_file"], "template back"
        ).read_text(encoding="utf-8")
        require(imported.get("qfmt") == front, "imported front template differs")
        require(imported.get("afmt") == back, "imported back template differs")


def compare_notes(manifest: LoadedManifest, collection: Collection) -> None:
    imported_notes = collection.find_notes("")
    require(len(imported_notes) == len(manifest.notes), "imported note count differs")

    by_guid: dict[str, Any] = {}
    for note_id in imported_notes:
        note = collection.get_note(note_id)
        by_guid[note.guid] = note
    require(len(by_guid) == len(imported_notes), "imported notes contain duplicate GUIDs")

    for expected in manifest.notes:
        guid = expected["guid"]
        require(guid in by_guid, f"imported note is missing: {guid}")
        note = by_guid[guid]
        require(note.id == expected["id"], f"imported note ID differs: {guid}")
        require(note.mid == manifest.notetype["id"], f"imported note type differs: {guid}")
        require(note.fields == expected["fields"], f"imported note fields differ: {guid}")
        require(note.tags == expected.get("tags", []), f"imported note tags differ: {guid}")

        expected_ords = sorted(card["ord"] for card in expected["cards"])
        imported_ords = sorted(collection.get_card(card_id).ord for card_id in note.card_ids())
        require(imported_ords == expected_ords, f"imported card orders differ: {guid}")


def compare_media(manifest: LoadedManifest, collection: Collection) -> None:
    media_dir = Path(collection.media.dir())
    expected_names = {item["name"] for item in manifest.media}
    imported_names = {path.name for path in media_dir.iterdir() if path.is_file()}
    require(imported_names == expected_names, "imported media names differ")

    for item in manifest.media:
        imported = media_dir / item["name"]
        require(imported.stat().st_size == item["size"], f"imported media size differs: {item['name']}")
        require(
            sha256_file(imported) == item["sha256"],
            f"imported media hash differs: {item['name']}",
        )


def check_package(manifest: LoadedManifest, package_path: Path) -> dict[str, Any]:
    if not package_path.is_file():
        raise CompatibilityError(f"package does not exist: {package_path}")

    with tempfile.TemporaryDirectory(prefix="anki-build-check-") as temp_dir:
        collection = Collection(str(Path(temp_dir) / "collection.anki2"))
        try:
            collection.import_anki_package(
                ImportAnkiPackageRequest(package_path=str(package_path.resolve()))
            )
            require(
                collection.note_count() == len(manifest.notes),
                "imported note count differs",
            )
            require(
                collection.card_count()
                == sum(len(note["cards"]) for note in manifest.notes),
                "imported card count differs",
            )

            model = collection.models.get(manifest.notetype["id"])
            require(model is not None, "imported source note type is missing")
            compare_model(manifest, model)
            compare_notes(manifest, collection)
            compare_media(manifest, collection)
        finally:
            collection.close()

    return {
        "package": str(package_path),
        "name": manifest.name,
        "notes": len(manifest.notes),
        "cards": sum(len(note["cards"]) for note in manifest.notes),
        "media": len(manifest.media),
        "anki_compatible": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser(
        "check",
        help="import a package into a temporary Anki collection and verify it",
    )
    check_parser.add_argument("--manifest", required=True, type=Path)
    check_parser.add_argument("--package", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "check":
            manifest = load_manifest(args.manifest)
            report = check_package(manifest, args.package.resolve())
            print(
                f"Anki compatibility check passed: {report['notes']} notes, "
                f"{report['cards']} cards, {report['media']} media files."
            )
            return 0
    except (CompatibilityError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
