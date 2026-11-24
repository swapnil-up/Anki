from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .manifest import LoadedManifest, safe_source_path


COLLECTION_FIELD_SEPARATOR = "\x1f"
ZIP_TIMESTAMP = (2024, 1, 1, 0, 0, 0)


SCHEMA = """
CREATE TABLE col (
    id integer primary key,
    crt integer not null,
    mod integer not null,
    scm integer not null,
    ver integer not null,
    dty integer not null,
    usn integer not null,
    ls integer not null,
    conf text not null,
    models text not null,
    decks text not null,
    dconf text not null,
    tags text not null
);
CREATE TABLE notes (
    id integer primary key,
    guid text not null,
    mid integer not null,
    mod integer not null,
    usn integer not null,
    tags text not null,
    flds text not null,
    sfld integer not null,
    csum integer not null,
    flags integer not null,
    data text not null
);
CREATE TABLE cards (
    id integer primary key,
    nid integer not null,
    did integer not null,
    ord integer not null,
    mod integer not null,
    usn integer not null,
    type integer not null,
    queue integer not null,
    due integer not null,
    ivl integer not null,
    factor integer not null,
    reps integer not null,
    lapses integer not null,
    left integer not null,
    odue integer not null,
    odid integer not null,
    flags integer not null,
    data text not null
);
CREATE TABLE revlog (
    id integer primary key,
    cid integer not null,
    usn integer not null,
    ease integer not null,
    ivl integer not null,
    lastIvl integer not null,
    factor integer not null,
    time integer not null,
    type integer not null
);
CREATE TABLE graves (
    usn integer not null,
    oid integer not null,
    type integer not null
);
CREATE INDEX ix_notes_usn ON notes (usn);
CREATE INDEX ix_cards_usn ON cards (usn);
CREATE INDEX ix_revlog_usn ON revlog (usn);
CREATE INDEX ix_cards_nid ON cards (nid);
CREATE INDEX ix_cards_sched ON cards (did, queue, due);
CREATE INDEX ix_revlog_cid ON revlog (cid);
CREATE INDEX ix_notes_csum ON notes (csum);
"""


DEFAULT_DECK_CONFIG = {
    "1": {
        "autoplay": True,
        "id": 1,
        "lapse": {
            "delays": [10],
            "leechAction": 0,
            "leechFails": 8,
            "minInt": 1,
            "mult": 0,
        },
        "maxTaken": 60,
        "mod": 0,
        "name": "Default",
        "new": {
            "bury": True,
            "delays": [1, 10],
            "initialFactor": 2500,
            "ints": [1, 4, 7],
            "order": 1,
            "perDay": 20,
            "separate": True,
        },
        "replayq": True,
        "rev": {
            "bury": True,
            "ease4": 1.3,
            "fuzz": 0.05,
            "ivlFct": 1,
            "maxIvl": 36500,
            "minSpace": 1,
            "perDay": 100,
        },
        "timer": 0,
        "usn": 0,
    }
}


def compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def field_checksum(value: str) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16)


def model_json(manifest: LoadedManifest) -> dict[str, Any]:
    notetype = manifest.notetype
    deck_id = manifest.deck["id"]
    templates = []
    for template in sorted(notetype["templates"], key=lambda item: item["ord"]):
        front_path = safe_source_path(
            manifest.base_dir, template["front_file"], "template front"
        )
        back_path = safe_source_path(
            manifest.base_dir, template["back_file"], "template back"
        )
        templates.append(
            {
                "name": template["name"],
                "ord": template["ord"],
                "qfmt": front_path.read_text(encoding="utf-8"),
                "afmt": back_path.read_text(encoding="utf-8"),
                "did": deck_id,
                "bqfmt": "",
                "bafmt": "",
                "bfont": "",
                "bsize": 0,
                "browserFontName": "",
                "browserFontSize": 0,
            }
        )

    fields = []
    for field in sorted(notetype["fields"], key=lambda item: item["ord"]):
        fields.append(
            {
                "name": field["name"],
                "ord": field["ord"],
                "sticky": bool(field.get("sticky", False)),
                "rtl": bool(field.get("rtl", False)),
                "font": field.get("font", "Arial"),
                "size": field.get("size", 20),
                "media": [],
                "description": field.get("description", ""),
                "plainText": bool(field.get("plain_text", False)),
                "collapsed": bool(field.get("collapsed", False)),
                "excludeFromSearch": bool(field.get("exclude_from_search", False)),
                "preventDeletion": False,
                "tag": None,
            }
        )

    css_path = safe_source_path(manifest.base_dir, notetype["css_file"], "CSS")
    return {
        "id": str(notetype["id"]),
        "name": notetype["name"],
        "type": notetype.get("kind", 0),
        "mod": notetype.get("mod", 0),
        "usn": notetype.get("usn", -1),
        "sortf": notetype.get("sort_field", 0),
        "did": deck_id,
        "tmpls": templates,
        "flds": fields,
        "css": css_path.read_text(encoding="utf-8"),
        "latexPre": "",
        "latexPost": "",
        "latexsvg": False,
        "req": notetype["requirements"],
        "tags": [],
        "vers": [],
        "originalId": notetype["id"],
    }


def deck_json(manifest: LoadedManifest) -> dict[str, Any]:
    deck = manifest.deck
    return {
        "id": deck["id"],
        "name": deck["name"],
        "mod": deck.get("mod", 0),
        "usn": deck.get("usn", -1),
        "lrnToday": [0, 0],
        "revToday": [0, 0],
        "newToday": [0, 0],
        "timeToday": [0, 0],
        "collapsed": False,
        "browserCollapsed": False,
        "conf": 1,
        "dyn": 0,
        "extendNew": 10,
        "extendRev": 50,
        "desc": "",
    }


def collection_json(manifest: LoadedManifest) -> tuple[str, str, str, str, str]:
    deck_id = manifest.deck["id"]
    conf = {
        "activeDecks": [deck_id],
        "addToCur": True,
        "collapseTime": 1200,
        "curDeck": deck_id,
        "curModel": str(manifest.notetype["id"]),
        "dueCounts": True,
        "estTimes": True,
        "newBury": True,
        "newSpread": 0,
        "nextPos": 1,
        "sortBackwards": False,
        "sortType": "noteFld",
        "timeLim": 0,
    }
    models = {str(manifest.notetype["id"]): model_json(manifest)}
    decks = {
        "1": {
            "collapsed": False,
            "conf": 1,
            "desc": "",
            "dyn": 0,
            "extendNew": 10,
            "extendRev": 50,
            "id": 1,
            "lrnToday": [0, 0],
            "mod": 0,
            "name": "Default",
            "newToday": [0, 0],
            "revToday": [0, 0],
            "timeToday": [0, 0],
            "usn": 0,
        },
        str(deck_id): deck_json(manifest),
    }
    return (
        compact_json(conf),
        compact_json(models),
        compact_json(decks),
        compact_json(DEFAULT_DECK_CONFIG),
        compact_json({}),
    )


def build_collection(manifest: LoadedManifest) -> bytes:
    conf, models, decks, dconf, tags = collection_json(manifest)
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("PRAGMA page_size = 4096")
        connection.execute("PRAGMA auto_vacuum = NONE")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = OFF")
        connection.execute("PRAGMA secure_delete = OFF")
        connection.execute("PRAGMA locking_mode = EXCLUSIVE")
        connection.executescript(SCHEMA)
        connection.execute(
            "INSERT INTO col VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                manifest.deck.get("mod", 0),
                manifest.deck.get("mod", 0),
                manifest.deck.get("mod", 0) * 1000 + 1,
                11,
                0,
                -1,
                0,
                conf,
                models,
                decks,
                dconf,
                tags,
            ),
        )

        notetype_id = manifest.notetype["id"]
        for note in manifest.notes:
            fields = note["fields"]
            raw_tags = note.get("raw_tags")
            if raw_tags is None:
                raw_tags = " " + " ".join(note.get("tags", [])) + " "
            sort_field = note.get("sort_field", fields[0])
            connection.execute(
                "INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    note["id"],
                    note["guid"],
                    notetype_id,
                    note.get("mod", 0),
                    note.get("usn", -1),
                    raw_tags,
                    COLLECTION_FIELD_SEPARATOR.join(fields),
                    sort_field,
                    field_checksum(fields[0]),
                    note.get("flags", 0),
                    note.get("data", ""),
                ),
            )
            for card in sorted(note["cards"], key=lambda item: item["ord"]):
                connection.execute(
                    "INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        card["id"],
                        note["id"],
                        manifest.deck["id"],
                        card["ord"],
                        card.get("mod", 0),
                        card.get("usn", -1),
                        card.get("type", 0),
                        card.get("queue", 0),
                        card.get("due", 0),
                        card.get("ivl", 0),
                        card.get("factor", 0),
                        card.get("reps", 0),
                        card.get("lapses", 0),
                        card.get("left", 0),
                        card.get("odue", 0),
                        card.get("odid", 0),
                        card.get("flags", 0),
                        card.get("data", "{}"),
                    ),
                )

        connection.commit()
        connection.execute("VACUUM")
        return connection.serialize()
    finally:
        connection.close()


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits = 0
    return info


def build_package(manifest: LoadedManifest, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    collection = build_collection(manifest)
    media = sorted(manifest.media, key=lambda item: item["index"])
    media_map = {str(item["index"]): item["name"] for item in media}

    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", dir=output_path.parent
    )
    os.close(temporary_fd)
    temporary_path = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary_path,
            "w",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            archive.writestr(zip_info("collection.anki2"), collection)
            for item in media:
                source = safe_source_path(
                    manifest.base_dir, item["file"], f"media {item['name']}"
                )
                archive.writestr(zip_info(str(item["index"])), source.read_bytes())
            archive.writestr(
                zip_info("media"),
                compact_json(media_map).encode("utf-8"),
            )
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
