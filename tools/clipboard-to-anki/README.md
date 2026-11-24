# Clipboard to Anki

`add-to-anki.sh` captures selected text and opens Anki's Add dialog through AnkiConnect. It captures the active window before it starts Anki, so the source title still refers to the document or page where you selected the text.

## Requirements

- Bash 4.4 or newer
- Anki with AnkiConnect
- `curl`, `jq`, `xclip`, and `xprop`
- `anki` on `PATH` when automatic launch is enabled

The script targets X11 on Linux.

## Usage

```bash
./add-to-anki.sh
```

The default profile sends the selection to the `Text` field of a `Cloze` note in the `Testing` deck. Source metadata goes to `Back Extra`.

Run `./add-to-anki.sh --help` for command-line options.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `ANKI_CONNECT_URL` | `http://127.0.0.1:8765` | AnkiConnect endpoint |
| `ANKI_CONNECT_API_KEY` | unset | Sends an AnkiConnect API key |
| `ANKI_DECK` | `Testing` | Destination deck |
| `ANKI_MODEL` | `Cloze` | Note type |
| `ANKI_TEXT_FIELD` | `Text` | Field receiving selected text |
| `ANKI_EXTRA_FIELD` | `Back Extra` | Field receiving source metadata |
| `ANKI_TAGS` | unset | Comma-separated tags |
| `ANKI_LAUNCH` | `true` | Start Anki if AnkiConnect is unavailable |
| `ANKI_DEBUG` | `off` | `off`, `metadata`, or `full` |
| `ANKI_ALLOW_MISSING_EXTRA_FIELD` | `false` | Omit the extra field when the model lacks it |
| `ANKI_HTTP_TIMEOUT` | `10` | AnkiConnect request timeout in seconds |
| `ANKI_READY_TIMEOUT` | `8` | Anki startup wait in seconds |

Command-line options override environment variables.

```bash
export ANKI_DECK="Reading"
export ANKI_CONNECT_API_KEY="secret"
./add-to-anki.sh --model Cloze --tags capture,reading
```

The script checks that the selected model contains the requested fields before it sends a note. If the model has no `Back Extra` field, either use `--allow-missing-extra-field` or set `ANKI_EXTRA_FIELD` to an existing field.

## Privacy and logs

The default `off` mode creates no log. `metadata` mode records timestamps, status, deck, and model, but not selected text or request payloads. `full` mode records the payload and selection in:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/anki-tools/clipboard-to-anki.log
```

The script creates the log with mode `0600` and restricts its directory to mode `0700`.

## Tests

```bash
tests/run.sh
```

The test suite replaces X11, Anki, and AnkiConnect commands with temporary stubs. It does not contact a live Anki instance.
