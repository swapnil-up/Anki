# Kindle highlights to TSV

`highlights-to-tsv.sh` converts Kindle `MyClippings.txt` exports into files that Anki can import. Each highlight becomes one row with the quote and its `Added on` date.

## Requirements

- Bash 4.4 or newer
- Standard Unix tools: `awk`, `date`, `dirname`, `sed`, and `tr`

The parser uses Bash pattern matching instead of GNU-specific regular expressions.

## Usage

```bash
./highlights-to-tsv.sh --input-dir ~/Kindle/MyClippings
```

Options:

| Option | Purpose |
| --- | --- |
| `--input-dir DIR` | Read `.txt` files from `DIR`; defaults to the current directory |
| `--output-dir DIR` | Write `.tsv` files to `DIR`; defaults to the input directory |
| `--force` | Replace existing output files |
| `--help` | Show usage |

Each input file creates one output file:

```text
MyClippings.txt -> MyClippings.tsv
```

The converter refuses to overwrite an existing output unless you pass `--force`.

## Output format

The first row is:

```text
Quote|Added On
```

The delimiter remains `|`. Select that separator in Anki's text importer. The `.tsv` extension describes one row per highlight; it does not imply that the fields use tabs.

The converter:

- wraps each field in double quotes;
- doubles embedded double quotes;
- keeps embedded pipes inside the quoted quote field;
- normalizes multi-line highlights to one row;
- leaves the date empty when the source has no `Added on` metadata.

## Import into Anki

1. Run the converter.
2. In Anki, choose **Import** and select the `.tsv` file.
3. Set the separator to `|`.
4. Map the first field to `Text` and the second field to `Back Extra`.
5. Choose the Cloze note type and add cloze deletions in the editor.

## Tests

```bash
tests/run.sh
```

The fixture suite covers common Kindle layouts, multiple books, quoted text, embedded pipes, multi-line highlights, missing dates, empty input, and overwrite protection.
