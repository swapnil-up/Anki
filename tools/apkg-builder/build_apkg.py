#!/usr/bin/env python3
"""Build a deterministic legacy Anki package from a source manifest."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from anki_build.legacy import build_package
from anki_build.manifest import ManifestError, load_manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="build a deterministic APKG package",
    )
    build_parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="path to a deck source manifest",
    )
    build_parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="output APKG path",
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(manifest_path: Path, output_path: Path) -> int:
    manifest = load_manifest(manifest_path)
    build_package(manifest, output_path.resolve())
    print(f"Built {output_path} ({sha256_file(output_path.resolve())})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "build":
            return build(args.manifest, args.out)
    except (ManifestError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
