# Programming Cloze card

A Cloze note type for recalling code by typing it. The card gives you a real multiline editor, compares your response with the hidden Cloze answer, and shows a line-by-line diff after you reveal the solution.

The editor and comparison logic run locally in Anki. They do not call a network service.

## What changed

- A multiline code editor replaces Anki's single-line typing box while keeping Anki's native answer capture.
- `Tab` and `Shift+Tab` indent and outdent code.
- `Enter` inserts a newline. `Ctrl+Enter`, `Cmd+Enter`, or `Alt+Enter` reveals the answer.
- Three comparison modes handle whitespace differently.
- A live verdict shows whether the response matches under the selected mode.
- An optional whitespace view marks spaces, tabs, and non-breaking spaces.
- The answer side shows the expected code and your response as aligned line diffs.
- The layout supports narrow screens and Anki's night mode.

## Install

### 1. Create the note type

1. Open **Tools → Manage Note Types**.
2. Select **Add**, then clone the built-in **Cloze** note type.
3. Name the copy, for example `Programming Cloze`.
4. Rename the cloned type's `Extra` field to `Back Extra`.
5. Add a `Type Hint` field.
6. Put the fields in this order:

   | Field | Required | Purpose |
   | --- | --- | --- |
   | `Text` | Yes | The code prompt and Cloze deletions |
   | `Type Hint` | No | A short hint shown above the editor |
   | `Back Extra` | No | Notes or references shown after the diff |

### 2. Install the editor script

Copy the media file into your Anki profile's `collection.media` directory:

```bash
cp card-types/programming-cloze/media/_programming-cloze.js \
  "$HOME/.local/share/Anki2/User 1/collection.media/_programming-cloze.js"
```

Replace `User 1` with your profile directory. The filename must remain `_programming-cloze.js`, including the leading underscore.

On systems that store Anki data elsewhere, find the profile directory under `Anki2` and copy the file into its `collection.media` folder.

### 3. Install the templates

Open the note type's **Cards** tab. Paste these files into the matching fields:

| Anki field | Repository file |
| --- | --- |
| Front template | [`front.html`](front.html) |
| Back template | [`back.html`](back.html) |
| Styling | [`styling.css`](styling.css) |

Save the note type, then reload the browser if Anki already has the card open.

## Write a card

Put the Cloze deletion inside the `Text` field. Use `<pre><code>` when the surrounding code needs line breaks:

```html
<pre><code>if value > 0:
    {{c1::return "positive"}}
</code></pre>
```

For a multiline answer, put the whole deletion inside the code block:

```html
<pre><code>{{c1::if value > 0:
    return "positive"}}</code></pre>
```

Escape the less-than character as `&lt;` when it appears in code. Use `Type Hint` for a nudge, such as the function name or expected return type. Use `Back Extra` for an explanation, test case, or reference.

## Comparison modes

Choose a mode above the editor. Anki remembers the choice between reviews.

| Mode | Ignores | Still checks |
| --- | --- | --- |
| **Exact** | Nothing | Every space, tab, and line break |
| **Ignore indentation** | Leading spaces and tabs on each line | Internal spaces, trailing spaces, line breaks, and code |
| **Ignore all whitespace** | All spaces, tabs, and line breaks | Code and letter case |

**Ignore indentation** is the default. It accepts a differently indented block without accepting changes such as `return  1` for `return 1`.

The verdict affects the card's feedback only. You still choose Anki's **Again**, **Hard**, **Good**, or **Easy** rating. The answer side also keeps Anki's built-in comparison in a collapsed section for reference.

## Editor shortcuts

| Shortcut | Action |
| --- | --- |
| `Enter` | Insert a newline |
| `Tab` | Insert two spaces, or indent selected lines |
| `Shift+Tab` | Remove one indentation level |
| `Ctrl+Enter`, `Cmd+Enter`, `Alt+Enter` | Reveal the answer |
| **Reveal answer** button | Reveal the answer |

## Files

```text
card-types/programming-cloze/
├── front.html
├── back.html
├── styling.css
├── media/
│   └── _programming-cloze.js
└── tests/
    ├── answer-check.test.mjs
    └── run.sh
```

Run the comparison and template tests with:

```bash
card-types/programming-cloze/tests/run.sh
```

The repository's `make test` target runs the same suite.

## Troubleshooting

### The editor still looks like a normal input box

Anki did not load `_programming-cloze.js`. Confirm that the file sits directly inside `collection.media`, that its name starts with an underscore, and that the front template contains:

```html
<script src="_programming-cloze.js"></script>
```

Close and reopen the card after copying the file. Anki's developer tools can show a missing-media request.

### The editor says that only whitespace differs

Turn on **Whitespace: hidden** to **Whitespace: visible** and inspect the marked characters. Check the `Text` field for HTML wrappers, trailing spaces, tabs, or non-breaking spaces that do not appear in the prompt.

### The prompt runs together on one line

Wrap the code context in `<pre><code>`. Plain field text does not preserve visual line breaks.

## Acknowledgements

This card type grew from Liam Gower's [Learn Code with Anki](https://www.liamgower.com/main-blog/learn-code-with-anki) and the template ideas in [leej11/anki-templates](https://github.com/leej11/anki-templates/blob/master/programming/).

Anki's [field and template documentation](https://docs.ankiweb.net/templates/fields.html) explains the native Cloze and type-answer filters used here.
