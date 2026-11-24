#!/usr/bin/env bash
set -Eeuo pipefail

TEST_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SCRIPT_DIR=$(cd -- "$TEST_DIR/.." && pwd)
SCRIPT="$SCRIPT_DIR/add-to-anki.sh"
TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT

fail() {
	printf 'FAIL: %s\n' "$*" >&2
	exit 1
}

pass() {
	printf 'PASS: %s\n' "$*"
}

make_stubs() {
	local case_dir=$1
	mkdir -p "$case_dir/bin" "$case_dir/state"

	cat >"$case_dir/bin/xclip" <<'EOF'
#!/usr/bin/env bash
if [[ ${MOCK_EMPTY_SELECTION:-false} == true ]]; then
	exit 0
fi
printf '%s' 'selected "text" | special & value'
EOF

	cat >"$case_dir/bin/xprop" <<'EOF'
#!/usr/bin/env bash
if [[ ${1:-} == -root ]]; then
	printf '%s\n' '_NET_ACTIVE_WINDOW: window id # 0x123'
else
	printf '%s\n' '_NET_WM_NAME(UTF8_STRING) = "Example document"'
	printf '%s\n' 'WM_CLASS(STRING) = "example", "Example"'
fi
EOF

	cat >"$case_dir/bin/curl" <<'EOF'
#!/usr/bin/env bash
payload=$(cat)
printf '%s\n' "$payload" >>"$MOCK_REQUEST_LOG"
action=$(jq -r '.action' <<<"$payload")
case $action in
version)
	printf '%s\n' '{"result":6,"error":null}'
	;;
modelFieldNames)
	fields=${MOCK_FIELDS:-["Text","Back Extra"]}
	jq -cn --argjson fields "$fields" '{result: $fields, error: null}'
	;;
guiAddCards)
	if [[ ${MOCK_MALFORMED:-false} == true ]]; then
		printf '%s\n' 'not-json'
	else
		printf '%s\n' '{"result":[123],"error":null}'
	fi
	;;
*)
	printf '%s\n' '{"error":"unexpected action","result":null}'
	;;
esac
EOF

	cat >"$case_dir/bin/pgrep" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF

	cat >"$case_dir/bin/anki" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

	chmod +x "$case_dir/bin"/*
}

run_case() {
	local name=$1
	local case_dir="$TEMP_ROOT/$name"
	make_stubs "$case_dir"
	printf '%s\n' "$case_dir"
}

run_script() {
	local case_dir=$1
	local fields=${TEST_FIELDS:-}
	shift
	[[ -n $fields ]] || fields='["Text","Back Extra"]'
	env \
		"PATH=$case_dir/bin:$PATH" \
		"MOCK_REQUEST_LOG=$case_dir/requests.jsonl" \
		"MOCK_FIELDS=$fields" \
		"XDG_STATE_HOME=$case_dir/state" \
		"ANKI_CONNECT_URL=http://127.0.0.1:8765" \
		"ANKI_LAUNCH=false" \
		"ANKI_DEBUG=off" \
		"$@"
}

case_dir=$(run_case default)
output=$(run_script "$case_dir" "$SCRIPT" 2>&1) || fail "default request failed: $output"
[[ $output == *'Opened the Anki Add dialog'* ]] || fail "missing success message"
gui_payload=$(jq -cs '[.[] | select(.action == "guiAddCards")] | last' "$case_dir/requests.jsonl")
[[ $(jq -r '.params.note.fields.Text' <<<"$gui_payload") == 'selected "text" | special & value' ]] ||
	fail "selected text was not preserved"
[[ $(jq -r '.params.note.fields["Back Extra"]' <<<"$gui_payload") == *'Source: Example document'* ]] ||
	fail "source metadata did not use Back Extra"
[[ $(jq -r '.params.note.fields | has("Extra")' <<<"$gui_payload") == false ]] ||
	fail "metadata was sent to the incorrect Extra field"
[[ ! -e "$case_dir/state/anki-tools/clipboard-to-anki.log" ]] || fail "off mode created a log"
pass "default payload uses Text and Back Extra"

case_dir=$(run_case api-key)
run_script "$case_dir" ANKI_CONNECT_API_KEY=secret-key "$SCRIPT" >/dev/null ||
	fail "API-key request failed"
gui_payload=$(jq -cs '[.[] | select(.action == "guiAddCards")] | last' "$case_dir/requests.jsonl")
[[ $(jq -r '.key' <<<"$gui_payload") == secret-key ]] || fail "API key was not sent"
pass "AnkiConnect API key is included"

case_dir=$(run_case metadata-log)
run_script "$case_dir" ANKI_DEBUG=metadata "$SCRIPT" >/dev/null || fail "metadata log request failed"
log_file="$case_dir/state/anki-tools/clipboard-to-anki.log"
[[ -f $log_file ]] || fail "metadata log was not created"
grep -Fq 'selected "text"' "$log_file" && fail "metadata log contains selected text"
grep -Fq 'guiAddCards' "$log_file" && fail "metadata log contains request details"
pass "metadata logging omits selected text and payloads"

case_dir=$(run_case full-log)
run_script "$case_dir" ANKI_DEBUG=full "$SCRIPT" >/dev/null || fail "full log request failed"
log_file="$case_dir/state/anki-tools/clipboard-to-anki.log"
[[ -f $log_file ]] || fail "full log was not created"
grep -Fq 'selected "text"' "$log_file" || fail "full log does not contain selected text"
[[ $(stat -c '%a' "$log_file") == 600 ]] || fail "full log permissions are not 0600"
pass "full logging is explicit and uses mode 0600"

case_dir=$(run_case missing-field)
if TEST_FIELDS='["Text"]' run_script "$case_dir" "$SCRIPT" >"$case_dir/output" 2>&1; then
	fail "missing extra field was accepted"
fi
grep -Fq 'has no field' "$case_dir/output" || fail "missing field error was unclear"
if grep -Fq '"action":"guiAddCards"' "$case_dir/requests.jsonl"; then
	fail "note was sent after field validation failed"
fi
pass "invalid model fields fail before note creation"

case_dir=$(run_case empty-selection)
if run_script "$case_dir" MOCK_EMPTY_SELECTION=true "$SCRIPT" >"$case_dir/output" 2>&1; then
	fail "empty selection was accepted"
fi
grep -Fq 'empty' "$case_dir/output" || fail "empty selection error was unclear"
if [[ -f $case_dir/requests.jsonl ]] && grep -Fq '"action":"guiAddCards"' "$case_dir/requests.jsonl"; then
	fail "empty selection caused a note request"
fi
pass "empty selection fails without creating a note"

case_dir=$(run_case malformed-response)
if run_script "$case_dir" MOCK_MALFORMED=true "$SCRIPT" >"$case_dir/output" 2>&1; then
	fail "malformed AnkiConnect response was accepted"
fi
grep -Fq 'invalid JSON' "$case_dir/output" || fail "malformed response error was unclear"
pass "malformed AnkiConnect responses fail"

case_dir=$(run_case cli-override)
TEST_FIELDS='["Text","Context"]' run_script "$case_dir" "$SCRIPT" --extra-field Context >/dev/null ||
	fail "CLI field override failed"
gui_payload=$(jq -cs '[.[] | select(.action == "guiAddCards")] | last' "$case_dir/requests.jsonl")
[[ $(jq -r '.params.note.fields.Context' <<<"$gui_payload") == *'Source: Example document'* ]] ||
	fail "CLI extra-field override was ignored"
pass "command-line field overrides work"

printf '%s\n' 'All clipboard-to-Anki tests passed.'
