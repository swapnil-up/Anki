#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

PROGRAM_NAME=${0##*/}

CONFIG_URL=${ANKI_CONNECT_URL:-http://127.0.0.1:8765}
CONFIG_API_KEY=${ANKI_CONNECT_API_KEY-}
CONFIG_DECK=${ANKI_DECK:-Testing}
CONFIG_MODEL=${ANKI_MODEL:-Cloze}
CONFIG_TEXT_FIELD=${ANKI_TEXT_FIELD:-Text}
CONFIG_EXTRA_FIELD=${ANKI_EXTRA_FIELD:-Back Extra}
CONFIG_TAGS=${ANKI_TAGS-}
CONFIG_LAUNCH=${ANKI_LAUNCH:-true}
CONFIG_DEBUG=${ANKI_DEBUG:-off}
CONFIG_ALLOW_MISSING_EXTRA_FIELD=${ANKI_ALLOW_MISSING_EXTRA_FIELD:-false}
CONFIG_HTTP_TIMEOUT=${ANKI_HTTP_TIMEOUT:-10}
CONFIG_READY_TIMEOUT=${ANKI_READY_TIMEOUT:-8}

log_file=${XDG_STATE_HOME:-$HOME/.local/state}/anki-tools/clipboard-to-anki.log
launch_anki=true

usage() {
	cat <<EOF
Usage: $PROGRAM_NAME [options]

Capture selected text and open it in Anki through AnkiConnect.

Options:
  --url URL                    AnkiConnect URL
  --api-key KEY                AnkiConnect API key
  --deck NAME                  Destination deck
  --model NAME                 Note type
  --text-field NAME            Field receiving selected text
  --extra-field NAME           Field receiving source metadata
  --tags LIST                  Comma-separated tags
  --no-launch                  Do not start Anki automatically
  --allow-missing-extra-field  Permit a model without the extra field
  --debug LEVEL                off, metadata, or full
  --timeout SECONDS            AnkiConnect request timeout
  --help                       Show this help

Environment variables provide the defaults. Command-line options override them.
EOF
}

die() {
	printf '%s: %s\n' "$PROGRAM_NAME" "$*" >&2
	exit 1
}

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

parse_boolean() {
	case ${1,,} in
		true | 1 | yes | on)
			printf 'true'
			;;
		false | 0 | no | off)
			printf 'false'
			;;
		*)
			die "expected true or false, got: $1"
			;;
	esac
}

while (($#)); do
	case $1 in
		--url)
			[[ $# -ge 2 ]] || die "--url requires a value"
			CONFIG_URL=$2
			shift 2
			;;
		--api-key)
			[[ $# -ge 2 ]] || die "--api-key requires a value"
			CONFIG_API_KEY=$2
			shift 2
			;;
		--deck)
			[[ $# -ge 2 ]] || die "--deck requires a value"
			CONFIG_DECK=$2
			shift 2
			;;
		--model)
			[[ $# -ge 2 ]] || die "--model requires a value"
			CONFIG_MODEL=$2
			shift 2
			;;
		--text-field)
			[[ $# -ge 2 ]] || die "--text-field requires a value"
			CONFIG_TEXT_FIELD=$2
			shift 2
			;;
		--extra-field)
			[[ $# -ge 2 ]] || die "--extra-field requires a value"
			CONFIG_EXTRA_FIELD=$2
			shift 2
			;;
		--tags)
			[[ $# -ge 2 ]] || die "--tags requires a value"
			CONFIG_TAGS=$2
			shift 2
			;;
		--no-launch)
			launch_anki=false
			shift
			;;
		--allow-missing-extra-field)
			CONFIG_ALLOW_MISSING_EXTRA_FIELD=true
			shift
			;;
		--debug)
			[[ $# -ge 2 ]] || die "--debug requires a value"
			CONFIG_DEBUG=$2
			shift 2
			;;
		--timeout)
			[[ $# -ge 2 ]] || die "--timeout requires a value"
			CONFIG_HTTP_TIMEOUT=$2
			shift 2
			;;
		--help | -h)
			usage
			exit 0
			;;
		*)
			die "unknown option: $1"
			;;
	esac
done

case ${CONFIG_DEBUG,,} in
	off | metadata | full) ;;
	*) die "--debug must be off, metadata, or full" ;;
esac

require_command curl
require_command jq
require_command xclip
require_command xprop

CONFIG_LAUNCH=$(parse_boolean "$CONFIG_LAUNCH")
if [[ $launch_anki == false ]]; then
	CONFIG_LAUNCH=false
fi
CONFIG_ALLOW_MISSING_EXTRA_FIELD=$(parse_boolean "$CONFIG_ALLOW_MISSING_EXTRA_FIELD")

if [[ ! $CONFIG_HTTP_TIMEOUT =~ ^[0-9]+([.][0-9]+)?$ ]]; then
	die "timeout must be a number"
fi

mkdir -p "$(dirname "$log_file")"
chmod 700 "$(dirname "$log_file")" 2>/dev/null || true
chmod 600 "$log_file" 2>/dev/null || true

log_metadata() {
	[[ ${CONFIG_DEBUG,,} == metadata || ${CONFIG_DEBUG,,} == full ]] || return 0
	local timestamp
	timestamp=$(date --iso-8601=seconds)
	printf '%s %s\n' "$timestamp" "$*" >>"$log_file"
}

log_full() {
	[[ ${CONFIG_DEBUG,,} == full ]] || return 0
	local timestamp
	timestamp=$(date --iso-8601=seconds)
	printf '%s %s\n' "$timestamp" "$*" >>"$log_file"
}

anki_request() {
	local action=$1
	local params=${2-}
	local payload response

	payload=$(jq -n \
		--arg action "$action" \
		--arg key "$CONFIG_API_KEY" \
		--argjson params "$params" \
		'{
			action: $action,
			version: 6,
			params: $params
		}
		+ if $key == "" then {} else {key: $key} end')

	log_full "request action=$action payload=$payload"

	if ! response=$(printf '%s' "$payload" | curl \
		--silent \
		--show-error \
		--fail-with-body \
		--connect-timeout 2 \
		--max-time "$CONFIG_HTTP_TIMEOUT" \
		--header 'Content-Type: application/json' \
		--data-binary @- \
		"$CONFIG_URL" 2>&1); then
		log_metadata "request action=$action failed"
		die "AnkiConnect request failed: $response"
	fi

	if ! jq -e . >/dev/null 2>&1 <<<"$response"; then
		log_metadata "request action=$action returned invalid JSON"
		die "AnkiConnect returned invalid JSON"
	fi

	if ! jq -e '.error == null' >/dev/null <<<"$response"; then
		local error
		error=$(jq -r '.error // "unknown AnkiConnect error"' <<<"$response")
		log_metadata "request action=$action error=$error"
		die "AnkiConnect error: $error"
	fi

	printf '%s' "$response"
}

check_ankiconnect() {
	anki_request version '{}' >/dev/null
}

wait_for_ankiconnect() {
	local attempts deadline now
	attempts=0
	deadline=$((SECONDS + ${CONFIG_READY_TIMEOUT%.*}))
	while ((SECONDS < deadline)); do
		if check_ankiconnect 2>/dev/null; then
			return 0
		fi
		attempts=$((attempts + 1))
		sleep 0.4
	done
	log_metadata "AnkiConnect did not become ready"
	return 1
}

launch_anki_if_needed() {
	if check_ankiconnect 2>/dev/null; then
		return 0
	fi

	if [[ $CONFIG_LAUNCH != true ]]; then
		die "AnkiConnect is not available at $CONFIG_URL"
	fi

	require_command anki
	log_metadata "AnkiConnect unavailable; launching Anki"

	if command -v setsid >/dev/null 2>&1; then
		setsid anki >/dev/null 2>&1 &
	else
		anki >/dev/null 2>&1 &
	fi

	wait_for_ankiconnect || die "AnkiConnect did not become ready at $CONFIG_URL"
}

capture_selection() {
	local selection
	selection=$(xclip -o -selection primary 2>/dev/null || true)
	if [[ -z $selection ]]; then
		selection=$(xclip -o -selection clipboard 2>/dev/null || true)
	fi
	printf '%s' "$selection"
}

capture_source() {
	local window_id title class
	window_id=$(xprop -root _NET_ACTIVE_WINDOW 2>/dev/null | awk '{print $NF}')
	if [[ -z $window_id || $window_id == 0x0 ]]; then
		printf 'Unknown application'
		return 0
	fi

	title=$(xprop -id "$window_id" _NET_WM_NAME 2>/dev/null | sed -n 's/.*= "\(.*\)"$/\1/p' | head -n1)
	class=$(xprop -id "$window_id" WM_CLASS 2>/dev/null | sed -n 's/.*, "\(.*\)"$/\1/p' | head -n1)

	if [[ -n $title ]]; then
		printf '%s' "$title"
	elif [[ -n $class ]]; then
		printf '%s' "$class"
	else
		printf 'Unknown application'
	fi
}

selected_text=$(capture_selection)
[[ -n $selected_text ]] || die "the primary selection and clipboard are empty"

source_name=$(capture_source)
captured_at=$(date '+%Y-%m-%d %H:%M:%S')
extra_value="Source: $source_name
Captured: $captured_at"

launch_anki_if_needed

model_fields=$(anki_request modelFieldNames "$(jq -n --arg model "$CONFIG_MODEL" '{modelName: $model}')" |
	jq -r '.result[]?')

if [[ -z $model_fields ]]; then
	die "note type does not exist or has no fields: $CONFIG_MODEL"
fi

if ! grep -Fxq -- "$CONFIG_TEXT_FIELD" <<<"$model_fields"; then
	die "note type '$CONFIG_MODEL' has no field '$CONFIG_TEXT_FIELD'"
fi

if [[ -n $CONFIG_EXTRA_FIELD ]] && ! grep -Fxq -- "$CONFIG_EXTRA_FIELD" <<<"$model_fields"; then
	if [[ $CONFIG_ALLOW_MISSING_EXTRA_FIELD == true ]]; then
		CONFIG_EXTRA_FIELD=
	else
		die "note type '$CONFIG_MODEL' has no field '$CONFIG_EXTRA_FIELD' (use --allow-missing-extra-field to omit it)"
	fi
fi

tags_json=$(jq -nR --arg tags "$CONFIG_TAGS" '$tags | split(",") | map(gsub("^\\s+|\\s+$"; "")) | map(select(length > 0))')
fields_json=$(jq -n \
	--arg text_field "$CONFIG_TEXT_FIELD" \
	--arg text "$selected_text" \
	--arg extra_field "$CONFIG_EXTRA_FIELD" \
	--arg extra "$extra_value" \
	'{
		($text_field): $text
	}
	+ if $extra_field == "" then {} else {($extra_field): $extra} end')

payload=$(jq -n \
	--arg deck "$CONFIG_DECK" \
	--arg model "$CONFIG_MODEL" \
	--argjson fields "$fields_json" \
	--argjson tags "$tags_json" \
	'{
		action: "guiAddCards",
		version: 6,
		params: {
			note: {
				deckName: $deck,
				modelName: $model,
				fields: $fields,
				tags: $tags
			}
		}
	}')

if [[ -n $CONFIG_API_KEY ]]; then
	payload=$(jq --arg key "$CONFIG_API_KEY" '. + {key: $key}' <<<"$payload")
fi

log_full "selected text=$selected_text source=$source_name"
if ! response=$(printf '%s' "$payload" | curl \
	--silent \
	--show-error \
	--fail-with-body \
	--connect-timeout 2 \
	--max-time "$CONFIG_HTTP_TIMEOUT" \
	--header 'Content-Type: application/json' \
	--data-binary @- \
	"$CONFIG_URL" 2>&1); then
	log_metadata "guiAddCards request failed"
	die "AnkiConnect request failed: $response"
fi

if ! jq -e . >/dev/null 2>&1 <<<"$response"; then
	log_metadata "guiAddCards returned invalid JSON"
	die "AnkiConnect returned invalid JSON"
fi

if ! jq -e '.error == null' >/dev/null <<<"$response"; then
	error=$(jq -r '.error // "unknown AnkiConnect error"' <<<"$response")
	log_metadata "guiAddCards error=$error"
	die "AnkiConnect error: $error"
fi

log_metadata "opened Add dialog deck=$CONFIG_DECK model=$CONFIG_MODEL"
printf 'Opened the Anki Add dialog for %s.\n' "$CONFIG_DECK"
