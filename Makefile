SHELL := /bin/bash

PYTHON ?= python3
UV ?= uv
INSTALL_DIR ?= $(HOME)/.local/bin
DIST_DIR ?= dist

SHELL_FILES := $(shell find . -type f -name '*.sh' -not -path './.git/*' -not -path './.venv/*')
PYTHON_FILES := $(shell find tools -type f -name '*.py' 2>/dev/null)
DECK_MANIFESTS := \
	decks/random-math/source/deck.json \
	decks/nepal-districts/source/deck.json

.PHONY: help lint format test build-decks verify-decks canonical-check check install install-tools

help:
	@printf '%s\n' \
		'make lint          Run syntax, ShellCheck, and formatting checks' \
		'make test          Run fixture, JavaScript, and Python tests' \
		'make build-decks   Build deterministic APKG packages' \
		'make verify-decks  Verify built APKG packages against manifests' \
		'make check         Run every automated check' \
		'make install       Install command-line symlinks'

lint:
	@set -euo pipefail; \
	files=(); \
	while IFS= read -r -d '' file; do files+=("$$file"); done < <(find . -type f -name '*.sh' -not -path './.git/*' -not -path './.venv/*' -print0); \
	(($${#files[@]} > 0)) && printf '%s\0' "$${files[@]}" | xargs -0 -n1 bash -n
	@command -v shellcheck >/dev/null || { echo 'shellcheck is required' >&2; exit 1; }
	@set -euo pipefail; \
	files=(); \
	while IFS= read -r -d '' file; do files+=("$$file"); done < <(find . -type f -name '*.sh' -not -path './.git/*' -not -path './.venv/*' -print0); \
	(($${#files[@]} > 0)) && shellcheck "$${files[@]}"
	@command -v shfmt >/dev/null || { echo 'shfmt is required' >&2; exit 1; }
	@set -euo pipefail; \
	files=(); \
	while IFS= read -r -d '' file; do files+=("$$file"); done < <(find . -type f -name '*.sh' -not -path './.git/*' -not -path './.venv/*' -print0); \
	(($${#files[@]})) && shfmt -d -i 0 -ci "$${files[@]}"

format:
	@command -v shfmt >/dev/null || { echo 'shfmt is required' >&2; exit 1; }
	@set -euo pipefail; \
	files=(); \
	while IFS= read -r -d '' file; do files+=("$$file"); done < <(find . -type f -name '*.sh' -not -path './.git/*' -not -path './.venv/*' -print0); \
	(($${#files[@]})) && shfmt -w -i 0 -ci "$${files[@]}"

test:
	@set -euo pipefail; \
	if [[ -x tools/clipboard-to-anki/tests/run.sh ]]; then tools/clipboard-to-anki/tests/run.sh; fi; \
	if [[ -x tools/kindle-highlights/tests/run.sh ]]; then tools/kindle-highlights/tests/run.sh; fi; \
	if [[ -x decks/random-math/tests/run.sh ]]; then decks/random-math/tests/run.sh; fi; \
	if [[ -x card-types/programming-cloze/tests/run.sh ]]; then card-types/programming-cloze/tests/run.sh; fi; \
	if compgen -G 'tools/apkg-builder/tests/test_*.py' >/dev/null; then \
		$(PYTHON) -m unittest discover -s tools/apkg-builder/tests -p 'test_*.py'; \
	fi

build-decks:
	@mkdir -p $(DIST_DIR)/random-math $(DIST_DIR)/nepal-districts
	$(PYTHON) tools/apkg-builder/build_apkg.py build \
		--manifest decks/random-math/source/deck.json \
		--out $(DIST_DIR)/random-math/Random\ Math.apkg
	$(PYTHON) tools/apkg-builder/build_apkg.py build \
		--manifest decks/nepal-districts/source/deck.json \
		--out $(DIST_DIR)/nepal-districts/nepal\ districts\ on\ map.apkg

verify-decks:
	$(PYTHON) tools/apkg-builder/verify_apkg.py verify \
		--manifest decks/random-math/source/deck.json \
		--package $(DIST_DIR)/random-math/Random\ Math.apkg
	$(PYTHON) tools/apkg-builder/verify_apkg.py verify \
		--manifest decks/nepal-districts/source/deck.json \
		--package $(DIST_DIR)/nepal-districts/nepal\ districts\ on\ map.apkg

canonical-check:
	@set -euo pipefail; \
	find decks -name canonical.sha256 -print0 | while IFS= read -r -d '' checksum; do \
		sha256sum -c "$$checksum"; \
	done

check: lint test build-decks verify-decks canonical-check

install: install-tools

install-tools:
	@mkdir -p $(INSTALL_DIR)
	@install_link() { \
		local source="$$1" target="$$2"; \
		if [[ -L "$$target" && "$$(readlink "$$target")" == "$$source" ]]; then \
			printf 'already linked: %s -> %s\n' "$$target" "$$source"; \
		elif [[ -e "$$target" || -L "$$target" ]]; then \
			printf 'refusing to replace existing path: %s\n' "$$target" >&2; \
			exit 1; \
		else \
			ln -s "$$source" "$$target"; \
			printf 'linked: %s -> %s\n' "$$target" "$$source"; \
		fi; \
	}; \
	install_link "$$(pwd)/tools/clipboard-to-anki/add-to-anki.sh" "$(INSTALL_DIR)/anki-add-to-anki"; \
	install_link "$$(pwd)/tools/kindle-highlights/highlights-to-tsv.sh" "$(INSTALL_DIR)/anki-highlights-to-tsv"
