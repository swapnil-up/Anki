#!/usr/bin/env bash
set -Eeuo pipefail

TEST_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

command -v node >/dev/null 2>&1 || {
  printf '%s\n' 'node is required to run the Programming Cloze tests' >&2
  exit 1
}

node --test "$TEST_DIR/answer-check.test.mjs"
