from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from .manifest import LoadedManifest, safe_source_path


COLLECTION_FIELD_SEPARATOR = "\x1f"


class VerificationError(ValueError):
    """Raised when a built package differs from its source manifest."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_collection(data: bytes) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.deserialize(data)
    connection.row_factory = sqlite3.Row
    return connection


def compare_model(manifest: LoadedManifest, model: dict[str, Any]) -> None:
    notetype = manifest.notetype
    require(str(model.get("id")) == str(notetype["id"]), "note type ID differs")
    require(model.get("name") == notetype["name"], "note type name differs")
    require(model.get("type") == notetype.get("kind", 0), "note type kind differs")
    require(
        model.get("sortf") == notetype.get("sort_field", 0),
        "note type sort field differs",
    )
    require(model.get("req") == notetype["requirements"], "card requirements differ")
    require(model.get("did") == manifest.deck["id"], "note type deck ID differs")

    css_path = safe_source_path(manifest.base_dir, notetype["css_file"], "CSS")
    require(model.get("css") == css_path.read_text(encoding="utf-8"), "CSS differs")

    package_fields = model.get("flds", [])
    require(len(package_fields) == len(notetype["fields"]), "field count differs")
    for expected, actual in zip(
        sorted(notetype["fields"], key=lambda item: item["ord"]),
        sorted(package_fields, key=lambda item: item["ord"]),
    ):
        require(actual.get("name") == expected["name"], "field name differs")
        require(actual.get("ord") == expected["ord"], "field order differs")
        require(actual.get("font") == expected.get("font", "Arial"), "field font differs")
        require(actual.get("size") == expected.get("size", 20), "field size differs")
        require(
            bool(actual.get("sticky", False)) == bool(expected.get("sticky", False)),
            "field sticky setting differs",
        )

    package_templates = model.get("tmpls", [])
    require(
        len(package_templates) == len(notetype["templates"]),
        "template count differs",
    )
    for expected, actual in zip(
        sorted(notetype["templates"], key=lambda item: item["ord"]),
        sorted(package_templates, key=lambda item: item["ord"]),
    ):
        require(actual.get("name") == expected["name"], "template name differs")
        require(actual.get("ord") == expected["ord"], "template order differs")
        front = safe_source_path(
            manifest.base_dir, expected["front_file"], "template front"
        ).read_text(encoding="utf-8")
        back = safe_source_path(
            manifest.base_dir, expected["back_file"], "template back"
        ).read_text(encoding="utf-8")
        require(actual.get("qfmt") == front, "front template differs")
        require(actual.get("afmt") == back, "back template differs")


def compare_notes(manifest: LoadedManifest, connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        "SELECT id, guid, mid, mod, usn, tags, flds, sfld, flags, data "
        "FROM notes ORDER BY id"
    ).fetchall()
    require(len(rows) == len(manifest.notes), "note count differs")
    package_notes = {row["guid"]: row for row in rows}
    require(len(package_notes) == len(rows), "package contains duplicate note GUIDs")

    for expected in manifest.notes:
        guid = expected["guid"]
        require(guid in package_notes, f"note is missing: {guid}")
        actual = package_notes[guid]
        require(actual["id"] == expected["id"], f"note ID differs: {guid}")
        require(actual["mid"] == manifest.notetype["id"], f"note type differs: {guid}")
        require(actual["mod"] == expected.get("mod", 0), f"note modification time differs: {guid}")
        require(actual["usn"] == expected.get("usn", -1), f"note USN differs: {guid}")
        expected_tags = expected.get("raw_tags")
        if expected_tags is None:
            expected_tags = " " + " ".join(expected.get("tags", [])) + " "
        require(actual["tags"] == expected_tags, f"note tags differ: {guid}")
        expected_fields = COLLECTION_FIELD_SEPARATOR.join(expected["fields"])
        require(actual["flds"] == expected_fields, f"note fields differ: {guid}")
        expected_sort = expected.get("sort_field", expected["fields"][0])
        require(actual["sfld"] == expected_sort, f"sort field differs: {guid}")
        require(actual["flags"] == expected.get("flags", 0), f"note flags differ: {guid}")
        require(actual["data"] == expected.get("data", ""), f"note data differs: {guid}")

        card_rows = connection.execute(
            "SELECT id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, "
            "lapses, left, odue, odid, flags, data FROM cards WHERE nid = ? ORDER BY ord",
            (expected["id"],),
        ).fetchall()
        require(
            len(card_rows) == len(expected["cards"]),
            f"card count differs for note: {guid}",
        )
        package_cards = {card["ord"]: card for card in card_rows}
        for expected_card in expected["cards"]:
            ord_value = expected_card["ord"]
            require(ord_value in package_cards, f"card is missing for note: {guid}")
            actual_card = package_cards[ord_value]
            require(
                actual_card["id"] == expected_card["id"],
                f"card ID differs for note: {guid}",
            )
            require(
                actual_card["did"] == manifest.deck["id"],
                f"card deck differs for note: {guid}",
            )
            for key in (
                "mod",
                "usn",
                "type",
                "queue",
                "due",
                "ivl",
                "factor",
                "reps",
                "lapses",
                "left",
                "odue",
                "odid",
                "flags",
            ):
                require(
                    actual_card[key] == expected_card.get(key, 0),
                    f"card {key} differs for note: {guid}",
                )
            require(
                actual_card["data"] == expected_card.get("data", "{}"),
                f"card data differs for note: {guid}",
            )


def verify_package(manifest: LoadedManifest, package_path: Path) -> dict[str, Any]:
    if not package_path.is_file():
        raise VerificationError(f"package does not exist: {package_path}")
    media = sorted(manifest.media, key=lambda item: item["index"])
    expected_names = ["collection.anki2"]
    expected_names.extend(str(item["index"]) for item in media)
    expected_names.append("media")

    with zipfile.ZipFile(package_path) as archive:
        require(archive.namelist() == expected_names, "package member order differs")
        collection_data = archive.read("collection.anki2")
        media_map = json.loads(archive.read("media").decode("utf-8"))
        expected_media_map = {str(item["index"]): item["name"] for item in media}
        require(media_map == expected_media_map, "media mapping differs")
        for item in media:
            data = archive.read(str(item["index"]))
            require(len(data) == item["size"], f"media size differs: {item['name']}")
            require(
                sha256_bytes(data) == item["sha256"],
                f"media hash differs: {item['name']}",
            )

    connection = open_collection(collection_data)
    try:
        col_rows = connection.execute("SELECT * FROM col").fetchall()
        require(len(col_rows) == 1, "collection metadata row is missing")
        col = col_rows[0]
        require(col["ver"] == 11, "collection schema version differs")
        models = json.loads(col["models"])
        decks = json.loads(col["decks"])
        model_id = str(manifest.notetype["id"])
        require(model_id in models, "source note type is missing")
        require(str(manifest.deck["id"]) in decks, "source deck is missing")
        compare_model(manifest, models[model_id])
        compare_notes(manifest, connection)
        card_count = connection.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        revlog_count = connection.execute("SELECT COUNT(*) FROM revlog").fetchone()[0]
        require(revlog_count == 0, "review history should be empty")
    finally:
        connection.close()

    return {
        "package": str(package_path),
        "name": manifest.name,
        "notes": len(manifest.notes),
        "cards": sum(len(note["cards"]) for note in manifest.notes),
        "media": len(manifest.media),
        "sha256": sha256_bytes(package_path.read_bytes()),
    }
