#!/usr/bin/env bash
set -Eeuo pipefail

TEST_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SCRIPT_DIR=$(cd -- "$TEST_DIR/.." && pwd)
SCRIPT="$SCRIPT_DIR/highlights-to-tsv.sh"
FIXTURES="$TEST_DIR/fixtures"
TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT

fail() {
	printf 'FAIL: %s\n' "$*" >&2
	exit 1
}

pass() {
	printf 'PASS: %s\n' "$*"
}

input_dir="$TEMP_ROOT/input"
output_dir="$TEMP_ROOT/output"
mkdir -p "$input_dir" "$output_dir"
cp "$FIXTURES"/*.txt "$input_dir"/

"$SCRIPT" --input-dir "$input_dir" --output-dir "$output_dir" >/dev/null ||
	fail "fixture conversion failed"

for expected in "$FIXTURES"/expected/*.tsv; do
	name=${expected##*/}
	actual="$output_dir/$name"
	[[ -f $actual ]] || fail "missing output: $name"
	diff -u "$expected" "$actual" || fail "output differs: $name"
done
pass "fixture outputs match"

empty_input="$TEMP_ROOT/empty-input"
empty_output="$TEMP_ROOT/empty-output"
mkdir -p "$empty_input" "$empty_output"
empty_message=$("$SCRIPT" --input-dir "$empty_input" --output-dir "$empty_output")
[[ $empty_message == *'No .txt files found'* ]] || fail "empty directory message was unclear"
[[ -z $(find "$empty_output" -type f -print -quit) ]] || fail "empty directory created an output file"
pass "empty input creates no output"

overwrite_input="$TEMP_ROOT/overwrite-input"
overwrite_output="$TEMP_ROOT/overwrite-output"
mkdir -p "$overwrite_input" "$overwrite_output"
cp "$FIXTURES/canonical.txt" "$overwrite_input/"
"$SCRIPT" --input-dir "$overwrite_input" --output-dir "$overwrite_output" >/dev/null ||
	fail "initial overwrite fixture failed"
if "$SCRIPT" --input-dir "$overwrite_input" --output-dir "$overwrite_output" >"$TEMP_ROOT/overwrite-error" 2>&1; then
	fail "existing output was overwritten without --force"
fi
grep -Fq 'already exists' "$TEMP_ROOT/overwrite-error" || fail "overwrite error was unclear"
"$SCRIPT" --input-dir "$overwrite_input" --output-dir "$overwrite_output" --force >/dev/null ||
	fail "--force did not replace the output"
diff -u "$FIXTURES/expected/canonical.tsv" "$overwrite_output/canonical.tsv" ||
	fail "forced output differs"
pass "existing output requires --force"

printf '%s\n' 'All Kindle highlights tests passed.'
