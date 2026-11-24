# APKG builder

This directory contains a source-driven Anki package builder and verifier. The builder writes a deterministic legacy `.apkg` from the JSON manifests under `decks/*/source/`.

The rebuilt package is not a byte-for-byte copy of the historical modern Anki export. It preserves the source manifest's notes, cards, note type, requirements, tags, scheduling values, and media in a legacy SQLite collection.

## Requirements

- Python 3.12
- `zstd` and Anki's bundled Python only when extracting or checking a modern package

The builder and verifier use only the Python standard library.

## Build a deck

```bash
python3 tools/apkg-builder/build_apkg.py build \
  --manifest decks/random-math/source/deck.json \
  --out dist/random-math/'Random Math.apkg'
```

The command validates the manifest and every declared source hash before it writes the package. It replaces the output atomically.

## Verify a deck

```bash
python3 tools/apkg-builder/verify_apkg.py verify \
  --manifest decks/random-math/source/deck.json \
  --package dist/random-math/'Random Math.apkg'
```

The verifier checks:

- deck and note type metadata;
- field order and properties;
- template contents and card requirements;
- note IDs, GUIDs, fields, tags, and sort fields;
- card IDs, template ordinals, deck IDs, and scheduling values;
- media names, indexes, sizes, and SHA-256 hashes;
- ZIP member order and an empty review history.

Use `--json` to print the report as JSON.

## Determinism

The writer uses explicit IDs from the manifest, a fixed SQLite schema and page size, deterministic JSON serialization, fixed ZIP timestamps and permissions, and stored media members. Two builds from the same manifest and source files produce the same SHA-256 digest in the pinned Python environment.

SQLite page bytes can differ between SQLite releases. Use semantic verification when comparing packages built by different toolchains.

## Extract a modern package

Anki 26.09.3 stores collection data in `collection.anki21b`, compressed with Zstandard. Extract a historical package with Anki's bundled Python:

```bash
PYTHONPATH=/usr/local/share/anki/app_packages \
  /usr/local/share/anki/python/bin/python \
  tools/apkg-builder/extract_modern.py \
  --package decks/random-math/'Random Math.apkg' \
  --output-dir /tmp/random-math-source \
  --force
```

The extractor writes templates, CSS, media, and `deck.json`. It is a migration aid; the committed manifests are the reviewed build inputs.

## Test

```bash
python3 -m unittest discover \
  -s tools/apkg-builder/tests \
  -p 'test_*.py'
```

The suite uses temporary manifests and packages. It does not modify a live Anki collection.
