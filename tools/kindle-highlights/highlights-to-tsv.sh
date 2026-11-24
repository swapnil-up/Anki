#!/usr/bin/env bash
set -Eeuo pipefail

PROGRAM_NAME=${0##*/}
INPUT_DIR=.
OUTPUT_DIR=
FORCE=false

usage() {
	cat <<EOF
Usage: $PROGRAM_NAME [options]

Convert Kindle MyClippings text exports into pipe-delimited TSV files.

Options:
  --input-dir DIR   Directory containing .txt files (default: current directory)
  --output-dir DIR  Directory for .tsv files (default: input directory)
  --force           Replace existing output files
  --help            Show this help

Each output file uses a pipe delimiter and has this header:
Quote|Added On
EOF
}

die() {
	printf '%s: %s\n' "$PROGRAM_NAME" "$*" >&2
	exit 1
}

while (($#)); do
	case $1 in
		--input-dir)
			[[ $# -ge 2 ]] || die "--input-dir requires a value"
			INPUT_DIR=$2
			shift 2
			;;
		--output-dir)
			[[ $# -ge 2 ]] || die "--output-dir requires a value"
			OUTPUT_DIR=$2
			shift 2
			;;
		--force)
			FORCE=true
			shift
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

[[ -d $INPUT_DIR ]] || die "input directory does not exist: $INPUT_DIR"
OUTPUT_DIR=${OUTPUT_DIR:-$INPUT_DIR}
[[ -d $OUTPUT_DIR ]] || die "output directory does not exist: $OUTPUT_DIR"

trim() {
	local value=$1
	value="${value#"${value%%[![:space:]]*}"}"
	value="${value%"${value##*[![:space:]]}"}"
	printf '%s' "$value"
}

escape_field() {
	local value=$1
	value=${value//\"/\"\"}
	printf '"%s"' "$value"
}

extract_added_on() {
	local line=$1
	if [[ $line == *"Added on "* ]]; then
		trim "${line#*Added on }"
	fi
}

write_entry() {
	local quote=$1
	local added_on=$2
	quote=$(trim "$quote")
	added_on=$(trim "$added_on")
	[[ -n $quote ]] || return 0
	printf '%s|%s\n' "$(escape_field "$quote")" "$(escape_field "$added_on")" >>"$output_file"
}

parse_file() {
	local input_file=$1
	local output_file=$2
	local -a lines=()
	local line next_line
	local quote=""
	local added_on=""
	local pending_blank=false
	local in_quote=false
	local index=0

	while IFS= read -r line || [[ -n $line ]]; do
		lines+=("${line%$'\r'}")
	done <"$input_file"

	printf 'Quote|Added On\n' >"$output_file"

	while ((index < ${#lines[@]})); do
		line=${lines[index]}
		next_line=""
		((index + 1 < ${#lines[@]})) && next_line=${lines[index + 1]}

		if [[ $line == '========'* ]]; then
			((index += 1))
			continue
		fi

		if [[ $line == '- '* ]]; then
			write_entry "$quote" "$added_on"
			quote=""
			added_on=$(extract_added_on "$line")
			pending_blank=false
			in_quote=true
			((index += 1))
			continue
		fi

		if [[ $in_quote == false ]]; then
			((index += 1))
			continue
		fi

		if [[ $line == 'Added on '* ]]; then
			added_on=$(trim "${line#Added on }")
			pending_blank=false
			((index += 1))
			continue
		fi

		if [[ -z $(trim "$line") ]]; then
			pending_blank=true
			((index += 1))
			continue
		fi

		if [[ $pending_blank == true && $next_line == '- '* ]]; then
			write_entry "$quote" "$added_on"
			quote=""
			added_on=""
			pending_blank=false
			in_quote=false
			((index += 1))
			continue
		fi

		if [[ -n $quote ]]; then
			quote+=" "
		fi
		quote+="$line"
		pending_blank=false
		((index += 1))
	done

	write_entry "$quote" "$added_on"
}

shopt -s nullglob
input_files=("$INPUT_DIR"/*.txt)
shopt -u nullglob

if ((${#input_files[@]} == 0)); then
	printf 'No .txt files found in %s\n' "$INPUT_DIR"
	exit 0
fi

for input_file in "${input_files[@]}"; do
	base_name=${input_file##*/}
	base_name=${base_name%.txt}
	output_file="$OUTPUT_DIR/$base_name.tsv"

	if [[ -e $output_file && $FORCE != true ]]; then
		die "output file already exists: $output_file (use --force to replace it)"
	fi

	parse_file "$input_file" "$output_file"
	printf 'Created %s\n' "$output_file"
done
