#!/usr/bin/env python3
"""Extract a modern Anki package into a source manifest and assets.

Run this script with Anki's bundled Python so its generated protobuf modules
are available. The resulting manifest can then be built with the standard
library-only builder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

try:
    from anki.decks_pb2 import Deck
    from anki.import_export_pb2 import MediaEntries
    from anki.notetypes_pb2 import Notetype
except ImportError as exc:  # pragma: no cover - depends on Anki installation
    raise SystemExit(
        "Run this script with Anki's bundled Python and PYTHONPATH set to "
        "Anki's app_packages directory."
    ) from exc


COLLECTION_FIELD_SEPARATOR = "\x1f"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def decompress_zstd(data: bytes) -> bytes:
    try:
        result = subprocess.run(
            ["zstd", "-dc"],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit("zstd is required to extract modern Anki packages") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"zstd failed to decompress a package member: {message}")
    return result.stdout


def open_modern_collection(package_path: Path) -> tuple[sqlite3.Connection, bytes]:
    with zipfile.ZipFile(package_path) as archive:
        try:
            compressed = archive.read("collection.anki21b")
        except KeyError as exc:
            raise SystemExit(f"package has no modern collection: {package_path}") from exc

    data = decompress_zstd(compressed)
    if len(data) < 20:
        raise SystemExit("modern collection is truncated")

    # Anki's exported modern collection retains WAL-style header markers even
    # when no WAL payload is present. A read-only connection can open it after
    # changing those markers to the rollback-journal values.
    data = data[:18] + b"\x01\x01" + data[20:]
    connection = sqlite3.connect(":memory:")
    connection.create_collation(
        "unicase",
        lambda left, right: (left.lower() > right.lower())
        - (left.lower() < right.lower()),
    )
    connection.deserialize(data)
    return connection, data


def only_row(rows: list[sqlite3.Row], label: str) -> sqlite3.Row:
    if len(rows) != 1:
        raise SystemExit(f"expected one {label}, found {len(rows)}")
    return rows[0]


def only_value(values: list[Any], label: str) -> Any:
    if len(values) != 1:
        raise SystemExit(f"expected one {label}, found {len(values)}")
    return values[0]


def template_filename(template_ord: int, template_count: int, side: str) -> str:
    if template_count == 1:
        return f"{side}.html"
    if template_count == 2:
        suffix = "reversed" if template_ord == 1 else ""
        return f"{side}{'-' + suffix if suffix else ''}.html"
    return f"template-{template_ord}-{side}.html"


def extract_media(
    archive: zipfile.ZipFile,
    output_dir: Path,
) -> list[dict[str, Any]]:
    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    raw_entries = decompress_zstd(archive.read("media"))
    entries = MediaEntries.FromString(raw_entries)
    result: list[dict[str, Any]] = []

    for index, entry in enumerate(entries.entries):
        member_name = str(index)
        try:
            compressed = archive.read(member_name)
        except KeyError as exc:
            raise SystemExit(f"package is missing media member {member_name}") from exc
        data = decompress_zstd(compressed)
        if len(data) != entry.size:
            raise SystemExit(
                f"media member {member_name} size mismatch: "
                f"expected {entry.size}, got {len(data)}"
            )
        if sha1_bytes(data) != entry.sha1.hex():
            raise SystemExit(f"media member {member_name} SHA-1 mismatch")

        target = media_dir / entry.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        result.append(
            {
                "index": index,
                "name": entry.name,
                "file": f"media/{entry.name}",
                "size": len(data),
                "sha1": entry.sha1.hex(),
                "sha256": sha256_bytes(data),
                "legacy_zip_filename": entry.legacy_zip_filename,
            }
        )

    return result


def extract(package_path: Path, output_dir: Path, force: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not force:
            raise SystemExit(f"output directory is not empty: {output_dir} (use --force)")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    connection, _ = open_modern_collection(package_path)
    connection.row_factory = sqlite3.Row
    try:
        deck_ids = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT did FROM cards ORDER BY did"
            ).fetchall()
        ]
        deck_id = only_value(deck_ids, "deck containing cards")
        note_type_ids = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT mid FROM notes ORDER BY mid"
            ).fetchall()
        ]
        notetype_id = only_value(note_type_ids, "note type containing notes")

        deck_row = only_row(
            connection.execute(
                "SELECT id, name, mtime_secs, usn FROM decks WHERE id = ?", (deck_id,)
            ).fetchall(),
            "deck",
        )
        notetype_row = only_row(
            connection.execute(
                "SELECT id, name, mtime_secs, usn, config FROM notetypes WHERE id = ?",
                (notetype_id,),
            ).fetchall(),
            "note type",
        )

        notetype_config = Notetype.Config.FromString(notetype_row["config"])
        kind_names = {0: "none", 1: "any", 2: "all"}
        requirements = [
            [
                requirement.card_ord,
                kind_names.get(requirement.kind, "none"),
                list(requirement.field_ords),
            ]
            for requirement in notetype_config.reqs
        ]

        fields: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT ntid, ord, name, config FROM fields WHERE ntid = ? ORDER BY ord",
            (notetype_id,),
        ):
            config = Notetype.Field.Config.FromString(row["config"])
            fields.append(
                {
                    "name": row["name"],
                    "ord": row["ord"],
                    "font": config.font_name or "Arial",
                    "size": config.font_size or 20,
                    "sticky": bool(config.sticky),
                    "rtl": bool(config.rtl),
                    "description": config.description,
                    "plain_text": bool(config.plain_text),
                    "collapsed": bool(config.collapsed),
                    "exclude_from_search": bool(config.exclude_from_search),
                }
            )

        templates: list[dict[str, Any]] = []
        template_rows = connection.execute(
            "SELECT ntid, ord, name, config FROM templates WHERE ntid = ? ORDER BY ord",
            (notetype_id,),
        ).fetchall()
        for row in template_rows:
            config = Notetype.Template.Config.FromString(row["config"])
            front_name = template_filename(row["ord"], len(template_rows), "front")
            back_name = template_filename(row["ord"], len(template_rows), "back")
            front_data = config.q_format.encode("utf-8")
            back_data = config.a_format.encode("utf-8")
            (output_dir / front_name).write_bytes(front_data)
            (output_dir / back_name).write_bytes(back_data)
            templates.append(
                {
                    "name": row["name"],
                    "ord": row["ord"],
                    "front_file": front_name,
                    "front_hash": sha256_bytes(front_data),
                    "back_file": back_name,
                    "back_hash": sha256_bytes(back_data),
                }
            )

        css_data = notetype_config.css.encode("utf-8")
        (output_dir / "styling.css").write_bytes(css_data)

        notes: list[dict[str, Any]] = []
        note_rows = connection.execute(
            "SELECT id, guid, mid, mod, usn, tags, flds, sfld, flags, data "
            "FROM notes WHERE mid = ? ORDER BY id",
            (notetype_id,),
        ).fetchall()
        for note_row in note_rows:
            cards: list[dict[str, Any]] = []
            card_rows = connection.execute(
                "SELECT id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, "
                "reps, lapses, left, odue, odid, flags, data FROM cards "
                "WHERE nid = ? ORDER BY ord",
                (note_row["id"],),
            ).fetchall()
            for card_row in card_rows:
                cards.append(
                    {
                        "id": card_row["id"],
                        "did": card_row["did"],
                        "ord": card_row["ord"],
                        "mod": card_row["mod"],
                        "usn": card_row["usn"],
                        "type": card_row["type"],
                        "queue": card_row["queue"],
                        "due": card_row["due"],
                        "ivl": card_row["ivl"],
                        "factor": card_row["factor"],
                        "reps": card_row["reps"],
                        "lapses": card_row["lapses"],
                        "left": card_row["left"],
                        "odue": card_row["odue"],
                        "odid": card_row["odid"],
                        "flags": card_row["flags"],
                        "data": card_row["data"],
                    }
                )
            raw_tags = note_row["tags"]
            notes.append(
                {
                    "id": note_row["id"],
                    "guid": note_row["guid"],
                    "mod": note_row["mod"],
                    "usn": note_row["usn"],
                    "tags": raw_tags.strip().split() if raw_tags.strip() else [],
                    "raw_tags": raw_tags,
                    "fields": note_row["flds"].split(COLLECTION_FIELD_SEPARATOR),
                    "sort_field": note_row["sfld"],
                    "flags": note_row["flags"],
                    "data": note_row["data"],
                    "cards": cards,
                }
            )
    finally:
        connection.close()

    with zipfile.ZipFile(package_path) as archive:
        media = extract_media(archive, output_dir)

    manifest = {
        "schema_version": 1,
        "name": deck_row["name"],
        "deck": {
            "id": deck_row["id"],
            "name": deck_row["name"],
            "mod": deck_row["mtime_secs"],
            "usn": deck_row["usn"],
        },
        "notetype": {
            "id": notetype_row["id"],
            "name": notetype_row["name"],
            "kind": notetype_config.kind,
            "sort_field": notetype_config.sort_field_idx,
            "mod": notetype_row["mtime_secs"],
            "usn": notetype_row["usn"],
            "fields": fields,
            "templates": templates,
            "requirements": requirements,
            "css_file": "styling.css",
            "css_hash": sha256_bytes(css_data),
        },
        "notes": notes,
        "media": media,
    }
    manifest_path = output_dir / "deck.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(notes)} notes and {len(media)} media files to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace a non-empty output directory",
    )
    args = parser.parse_args()
    extract(args.package.resolve(), args.output_dir.resolve(), args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
