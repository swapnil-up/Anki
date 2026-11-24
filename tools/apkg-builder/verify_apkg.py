#!/usr/bin/env python3
"""Verify an Anki package against its source manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from anki_build.manifest import ManifestError, load_manifest
from anki_build.verify import VerificationError, verify_package


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify",
        help="verify an APKG package against a source manifest",
    )
    verify_parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="path to a deck source manifest",
    )
    verify_parser.add_argument(
        "--package",
        required=True,
        type=Path,
        help="APKG package to verify",
    )
    verify_parser.add_argument(
        "--json",
        action="store_true",
        help="print the verification report as JSON",
    )
    return parser.parse_args(argv)


def verify(manifest_path: Path, package_path: Path, as_json: bool) -> int:
    manifest = load_manifest(manifest_path)
    report = verify_package(manifest, package_path.resolve())
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"Verified {package_path}: {report['notes']} notes, "
            f"{report['cards']} cards, {report['media']} media files."
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "verify":
            return verify(args.manifest, args.package, args.json)
    except (ManifestError, VerificationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
