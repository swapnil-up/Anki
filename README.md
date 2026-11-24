# Anki tools and decks

This repository collects Anki card templates, import tools, and two ready-to-import decks. It also keeps the source inputs used to rebuild those decks.

## Contents

| Component | Purpose |
| --- | --- |
| [`card-types/programming-cloze/`](card-types/programming-cloze/) | Multiline code-typing Cloze templates with whitespace-aware comparison |
| [`tools/clipboard-to-anki/`](tools/clipboard-to-anki/) | Capture selected text and open it in Anki through AnkiConnect |
| [`tools/kindle-highlights/`](tools/kindle-highlights/) | Convert Kindle `MyClippings.txt` files into pipe-delimited `.tsv` files |
| [`decks/random-math/`](decks/random-math/) | Dynamic square-practice cards and their source |
| [`decks/nepal-districts/`](decks/nepal-districts/) | Nepal district map cards and their source |
| [`tools/apkg-builder/`](tools/apkg-builder/) | Deterministic package builder and semantic verifier |

The original `.apkg` files remain available for direct import. Their SHA-256 hashes live beside each deck.

## Supported environment

The tools target Linux with X11. The repository is tested on Ubuntu 22.04 and 24.04.

| Requirement | Used by | Notes |
| --- | --- | --- |
| Bash 4.4+ | Shell tools | The scripts avoid GNU-only regular expressions |
| `curl` | Clipboard tool | Calls AnkiConnect over HTTP |
| `jq` | Clipboard tool | Builds and parses JSON without string interpolation |
| `xclip` | Clipboard tool | Reads primary selection, then clipboard selection |
| `xprop` | Clipboard tool | Reads the active-window title and class |
| `pgrep` | Clipboard tool | Checks whether Anki is running |
| Anki and AnkiConnect | Clipboard tool | AnkiConnect must expose its local API |
| Python 3.12 | Deck tooling | The builder uses the standard library |
| `uv` | Deck tooling | Creates the pinned development environment |
| Node.js 24 | JavaScript tests | Runs the Random Math and Programming Cloze tests |
| `zstd` | Source verification | Reads media in modern Anki packages |

The clipboard tool expects AnkiConnect at `http://127.0.0.1:8765` unless you configure another URL.

## Install

Clone the repository and check the tools:

```bash
git clone https://github.com/swapnil-up/anki.git
cd anki
make check
```

Install the two command-line tools into `~/.local/bin`:

```bash
make install
```

The install target creates symlinks. It refuses to replace an unrelated file with the same name.

## Clipboard to Anki

Configure AnkiConnect in Anki, then select text in a browser, PDF viewer, or e-book reader and run:

```bash
anki-add-to-anki
```

The default profile creates a Cloze note in the `Testing` deck. It puts the selected text in `Text` and the source and timestamp in `Back Extra`.

Common settings:

```bash
export ANKI_DECK="Reading"
export ANKI_MODEL="Cloze"
export ANKI_CONNECT_API_KEY="your-key"
anki-add-to-anki
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANKI_CONNECT_URL` | `http://127.0.0.1:8765` | AnkiConnect endpoint |
| `ANKI_CONNECT_API_KEY` | unset | Sends the key in the AnkiConnect request |
| `ANKI_DECK` | `Testing` | Destination deck |
| `ANKI_MODEL` | `Cloze` | Note type |
| `ANKI_TEXT_FIELD` | `Text` | Field that receives the selected text |
| `ANKI_EXTRA_FIELD` | `Back Extra` | Field that receives source metadata |
| `ANKI_TAGS` | unset | Comma-separated tags |
| `ANKI_LAUNCH` | `true` | Starts Anki when it is not running |
| `ANKI_DEBUG` | `off` | `off`, `metadata`, or `full` |

The command-line flags override environment variables. Run `anki-add-to-anki --help` for the complete list.

### Privacy

The tool does not log selected text, window titles, or request payloads by default. `ANKI_DEBUG=metadata` records status and timing only. `ANKI_DEBUG=full` writes the full payload to a private `0600` file under `${XDG_STATE_HOME:-$HOME/.local/state}/anki-tools/` only when you request it.

## Kindle highlights

Run the converter in the directory containing your Kindle text exports:

```bash
anki-highlights-to-tsv --input-dir ~/Kindle/MyClippings
```

Each input file produces a `.tsv` file with two fields:

```text
Quote|Added On
```

The delimiter remains `|`. Select that separator when importing the file into Anki. The converter quotes fields, escapes embedded quotes, preserves embedded pipes, and keeps one highlight on each output row.

The converter refuses to overwrite an existing output unless you pass `--force`.

## Decks

### Random Math

[`decks/random-math/`](decks/random-math/) contains five dynamic cards that practise calculating squares. The source directory preserves the note type, card requirement, notes, runtime, and original package hash.

The original package came from a third-party template whose upstream license grant is unclear. The repository retains it for provenance. Do not redistribute a rebuilt Random Math package until that licensing question is resolved.

### Nepal districts

[`decks/nepal-districts/`](decks/nepal-districts/) contains 77 forward and 77 reverse map cards. The source directory preserves all 82 media files, note data, card data, templates, and the original package hash.

The map remains under CC BY-SA 4.0. The bundled Anki Code Highlighter assets remain under AGPL-3.0. Any redistributed Nepal package must include the required map attribution, modification statement, AGPL notices, and corresponding-source offer.

## Rebuild and verify decks

The builder creates deterministic legacy Anki packages from the source manifests:

```bash
make build-decks
make verify-decks
```

Repeated builds have the same SHA-256 hash in the pinned Python environment. The output is semantically equivalent to the original modern Anki export, but it does not reproduce the original SQLite pages, Zstandard frames, or ZIP metadata byte for byte.

To check the whole repository:

```bash
make check
```

That command runs shell syntax checks, ShellCheck, formatting checks, fixture tests, JavaScript tests, deck builds, package verification, and canonical hash checks.

## Repository layout

```text
card-types/                 Reusable Anki templates
decks/                      Importable decks and source manifests
tools/                      Command-line tools and APKG tooling
```

## License

The repository-owned code and documentation use the [MIT License](LICENSE). The root MIT license does not relicense bundled libraries, map media, or other third-party materials. Review the deck-specific provenance and redistribution constraints before distributing a package.

## Contributions

Keep changes focused and include the relevant automated checks. Preserve the original package hashes unless the task explicitly replaces a canonical artifact.
