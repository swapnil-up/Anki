from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    """Raised when a deck manifest is invalid or inconsistent."""


@dataclass(frozen=True)
class LoadedManifest:
    path: Path
    data: dict[str, Any]
    base_dir: Path

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def deck(self) -> dict[str, Any]:
        return self.data["deck"]

    @property
    def notetype(self) -> dict[str, Any]:
        return self.data["notetype"]

    @property
    def notes(self) -> list[dict[str, Any]]:
        return self.data["notes"]

    @property
    def media(self) -> list[dict[str, Any]]:
        return self.data["media"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(f"{label} must be an integer")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{label} must be a non-empty string")
    return value


def require_sha256(value: Any, label: str) -> str:
    digest = require_string(value, label)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ManifestError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def safe_source_path(base_dir: Path, relative: str, label: str) -> Path:
    candidate = (base_dir / relative).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError as exc:
        raise ManifestError(f"{label} escapes the manifest directory: {relative}") from exc
    return candidate


def validate_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ManifestError(f"{label} hash mismatch: expected {expected}, got {actual}")


def load_manifest(path: str | Path) -> LoadedManifest:
    manifest_path = Path(path).resolve()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest does not exist: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be an object")
    if data.get("schema_version") != 1:
        raise ManifestError("manifest schema_version must be 1")

    base_dir = manifest_path.parent
    loaded = LoadedManifest(manifest_path, data, base_dir)

    require_string(data.get("name"), "name")
    deck = data.get("deck")
    if not isinstance(deck, dict):
        raise ManifestError("deck must be an object")
    require_int(deck.get("id"), "deck.id")
    require_string(deck.get("name"), "deck.name")
    require_int(deck.get("mod", 0), "deck.mod")
    require_int(deck.get("usn", -1), "deck.usn")

    notetype = data.get("notetype")
    if not isinstance(notetype, dict):
        raise ManifestError("notetype must be an object")
    require_int(notetype.get("id"), "notetype.id")
    require_string(notetype.get("name"), "notetype.name")
    require_int(notetype.get("kind", 0), "notetype.kind")
    require_int(notetype.get("sort_field", 0), "notetype.sort_field")

    fields = notetype.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ManifestError("notetype.fields must be a non-empty list")
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ManifestError(f"notetype.fields[{index}] must be an object")
        require_string(field.get("name"), f"notetype.fields[{index}].name")
        require_int(field.get("ord", index), f"notetype.fields[{index}].ord")
        require_string(field.get("font", "Arial"), f"notetype.fields[{index}].font")
        require_int(field.get("size", 20), f"notetype.fields[{index}].size")
        if not isinstance(field.get("sticky", False), bool):
            raise ManifestError(f"notetype.fields[{index}].sticky must be a boolean")

    templates = notetype.get("templates")
    if not isinstance(templates, list) or not templates:
        raise ManifestError("notetype.templates must be a non-empty list")
    for index, template in enumerate(templates):
        if not isinstance(template, dict):
            raise ManifestError(f"notetype.templates[{index}] must be an object")
        require_string(template.get("name"), f"notetype.templates[{index}].name")
        require_int(template.get("ord", index), f"notetype.templates[{index}].ord")
        for key in ("front_file", "back_file"):
            relative = require_string(template.get(key), f"notetype.templates[{index}].{key}")
            source_path = safe_source_path(base_dir, relative, f"notetype.templates[{index}].{key}")
            if not source_path.is_file():
                raise ManifestError(f"template source does not exist: {relative}")
            hash_key = f"{key.removesuffix('_file')}_hash"
            expected_hash = require_sha256(
                template.get(hash_key),
                f"notetype.templates[{index}].{hash_key}",
            )
            validate_hash(source_path, expected_hash, relative)

    requirements = notetype.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ManifestError("notetype.requirements must be a non-empty list")
    field_count = len(fields)
    template_count = len(templates)
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, list) or len(requirement) != 3:
            raise ManifestError(f"notetype.requirements[{index}] must contain three values")
        card_ord = require_int(requirement[0], f"notetype.requirements[{index}][0]")
        kind = requirement[1]
        if kind not in {"any", "all", "none"}:
            raise ManifestError(f"notetype.requirements[{index}][1] must be any, all, or none")
        allowed = requirement[2]
        if not isinstance(allowed, list) or not allowed:
            raise ManifestError(f"notetype.requirements[{index}][2] must be a non-empty list")
        if not 0 <= card_ord < template_count:
            raise ManifestError(f"card requirement references unknown template: {card_ord}")
        for field_ord in allowed:
            require_int(field_ord, f"notetype.requirements[{index}][2] entry")
            if not 0 <= field_ord < field_count:
                raise ManifestError(f"card requirement references unknown field: {field_ord}")

    css_file = require_string(notetype.get("css_file"), "notetype.css_file")
    css_path = safe_source_path(base_dir, css_file, "notetype.css_file")
    if not css_path.is_file():
        raise ManifestError(f"CSS source does not exist: {css_file}")
    css_hash = require_sha256(notetype.get("css_hash"), "notetype.css_hash")
    validate_hash(css_path, css_hash, css_file)

    notes = data.get("notes")
    if not isinstance(notes, list):
        raise ManifestError("notes must be a list")
    note_ids: set[int] = set()
    guids: set[str] = set()
    card_ids: set[int] = set()
    for note_index, note in enumerate(notes):
        if not isinstance(note, dict):
            raise ManifestError(f"notes[{note_index}] must be an object")
        note_id = require_int(note.get("id"), f"notes[{note_index}].id")
        if note_id in note_ids:
            raise ManifestError(f"duplicate note id: {note_id}")
        note_ids.add(note_id)
        guid = require_string(note.get("guid"), f"notes[{note_index}].guid")
        if guid in guids:
            raise ManifestError(f"duplicate note GUID: {guid}")
        guids.add(guid)
        require_int(note.get("mod", 0), f"notes[{note_index}].mod")
        require_int(note.get("usn", -1), f"notes[{note_index}].usn")
        fields_value = note.get("fields")
        if not isinstance(fields_value, list) or len(fields_value) != field_count:
            raise ManifestError(f"notes[{note_index}].fields must contain {field_count} values")
        if not all(isinstance(value, str) for value in fields_value):
            raise ManifestError(f"notes[{note_index}].fields values must be strings")
        tags = note.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ManifestError(f"notes[{note_index}].tags must be a list of strings")
        cards = note.get("cards")
        if not isinstance(cards, list) or not cards:
            raise ManifestError(f"notes[{note_index}].cards must be a non-empty list")
        for card_index, card in enumerate(cards):
            if not isinstance(card, dict):
                raise ManifestError(f"notes[{note_index}].cards[{card_index}] must be an object")
            card_id = require_int(card.get("id"), f"notes[{note_index}].cards[{card_index}].id")
            if card_id in card_ids:
                raise ManifestError(f"duplicate card id: {card_id}")
            card_ids.add(card_id)
            card_ord = require_int(card.get("ord"), f"notes[{note_index}].cards[{card_index}].ord")
            if not 0 <= card_ord < template_count:
                raise ManifestError(f"card references unknown template: {card_ord}")
            for key in (
                "mod",
                "usn",
                "due",
                "queue",
                "type",
                "factor",
                "ivl",
                "reps",
                "lapses",
                "left",
                "odue",
                "odid",
                "flags",
            ):
                require_int(card.get(key, 0), f"notes[{note_index}].cards[{card_index}].{key}")

    media = data.get("media", [])
    if not isinstance(media, list):
        raise ManifestError("media must be a list")
    media_names: set[str] = set()
    media_indexes: set[int] = set()
    for index, item in enumerate(media):
        if not isinstance(item, dict):
            raise ManifestError(f"media[{index}] must be an object")
        media_index = require_int(item.get("index"), f"media[{index}].index")
        if media_index in media_indexes:
            raise ManifestError(f"duplicate media index: {media_index}")
        media_indexes.add(media_index)
        name = require_string(item.get("name"), f"media[{index}].name")
        if name in media_names:
            raise ManifestError(f"duplicate media name: {name}")
        media_names.add(name)
        relative = require_string(item.get("file"), f"media[{index}].file")
        media_path = safe_source_path(base_dir, relative, f"media[{index}].file")
        if not media_path.is_file():
            raise ManifestError(f"media source does not exist: {relative}")
        expected_size = require_int(item.get("size"), f"media[{index}].size")
        if media_path.stat().st_size != expected_size:
            raise ManifestError(f"media size mismatch: {relative}")
        expected_hash = require_sha256(item.get("sha256"), f"media[{index}].sha256")
        validate_hash(media_path, expected_hash, relative)

    return loaded
