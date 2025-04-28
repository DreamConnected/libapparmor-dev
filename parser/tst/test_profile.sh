#!/usr/bin/env bash
set -euo pipefail

# Check if the current profile allow reading its attachment
check_entry() {
	local prof_name="$1"
	local -n lines_ref="$2"
	local attachment="$3"
	local found=0

	for line in "${lines_ref[@]}"; do
		if [[ $line == Perms:*r*:*"($attachment)"* ]]; then
			found=1
			break
		fi
	done

	if [[ $found -eq 0 ]]; then
		echo -e "\e[0;31mProfile $prof_name: ERROR: no Perms rule for '$attachment'.\e[0m"
		exit 1
	fi

	[[ -n "${VERBOSE:-}" ]] && echo -e "\e[0;32mProfile $prof_name: OK '$attachment' found\e[0m" || true
}

# Handle the end of a profile block: either skip it or check for the entry.
finish_profile() {
	local name="$1"
	local prof_file="$2"
	local skip="$3"
	local attachment="$4"
	local arr_name="$5"

	if [[ -n $name ]]; then
		if [[ $skip != 0 ]]; then
			[[ -n "${VERBOSE:-}" ]] && echo "Profile '$name' skipped: $skip" || true
		else
			check_entry "$prof_file ($name)" "$arr_name" "$attachment"
		fi
	fi
}

process_profile() {
	local prof_file="$1"
	shift
	local dump curr_name="" attachment="" skip_profile=0 in_entries=0
	local block_lines=()

	if ! dump=$(../parser/apparmor_parser $@ -d "$prof_file" 2>&1); then
		echo "\e[0;31mERROR: Failed to parse '$prof_file': $dump\e[0m" >&2
		exit 1
	fi

	IFS=$'\n' read -r -d '' -a lines < <(printf '%s\n' "$dump" && printf '\0')

	for line in "${lines[@]}"; do
		if [[ $line =~ ^[[:space:]]*Name:[[:space:]]*([^[:space:]]+) ]]; then
			finish_profile "$curr_name" "$prof_file" "$skip_profile" "$attachment" block_lines
			curr_name="${BASH_REMATCH[1]}"
			attachment="" skip_profile=0 in_entries=0 block_lines=()
		elif [[ $line =~ ^[[:space:]]*Mode:[[:space:]]*unconfined ]]; then
			skip_profile="unconfined"
		elif [[ $line =~ ^Perms:.*r.*:.*:.*\(/(\{?,?\*\*,*\}?)\) ]]; then
			skip_profile="All files available"
		elif [[ $line =~ ^[[:space:]]*Attachment:[[:space:]]*(.+) ]]; then
			attachment="${BASH_REMATCH[1]}"
			[[ $attachment == "<NULL>" ]] && skip_profile="no attachment"
		elif [[ $line == ---\ Entries\ --- ]]; then
			in_entries=1
		elif [[ $in_entries -ne 0 ]]; then
			block_lines+=("$line")
		fi
	done

	# Last profile
	finish_profile "$curr_name" "$prof_file" "$skip_profile" "$attachment" block_lines
}

if (( $# < 1 )); then
	echo "Usage: $0 <profile-file> [parser_extra_args]"
	exit 1
fi

process_profile $@
