import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const cardDir = path.resolve(testDir, "..");
const require = createRequire(import.meta.url);
const {
  MODES,
  MODE_LABELS,
  compareText,
  decodeEntitiesFallback,
  diffLines,
  getStorage,
  htmlToText,
  normalizeIndent,
  normalizeLoose,
  selectAnswerState,
} = require(path.join(cardDir, "media/_programming-cloze.js"));

test("exact comparison preserves spaces and line structure", () => {
  assert.equal(compareText("value = 1", "value = 1", MODES.EXACT).matches, true);
  assert.equal(compareText("value = 1", "value  = 1", MODES.EXACT).matches, false);
  assert.equal(compareText("one\ntwo", "one two", MODES.EXACT).matches, false);
  assert.equal(compareText("one\r\ntwo", "one\ntwo", MODES.EXACT).matches, true);
});

test("indentation mode ignores leading whitespace but not internal whitespace", () => {
  assert.equal(
    compareText("if value:\n    return 1", "if value:\n  return 1", MODES.INDENT)
      .matches,
    true,
  );
  assert.equal(
    compareText("if value:\n    return 1", "if value:\n    return  1", MODES.INDENT)
      .matches,
    false,
  );
  assert.equal(
    compareText("if value:\n    return 1", "if value:\n    return 1 ", MODES.INDENT)
      .matches,
    false,
  );
  assert.equal(
    compareText("one\ntwo", "one two", MODES.INDENT).matches,
    false,
  );
});

test("loose mode ignores every whitespace character", () => {
  assert.equal(
    compareText("if value:\n  return 1", "ifvalue:return1", MODES.LOOSE).matches,
    true,
  );
  assert.equal(
    compareText("one two", "one three", MODES.LOOSE).matches,
    false,
  );
});

test("normalizers expose the selected comparison semantics", () => {
  assert.equal(normalizeIndent("  one\n\t two  "), "one\ntwo  ");
  assert.equal(normalizeLoose(" one\t two\n"), "onetwo");
  assert.deepEqual(Object.keys(MODE_LABELS).sort(), [
    MODES.EXACT,
    MODES.INDENT,
    MODES.LOOSE,
  ]);
});

test("HTML-to-text conversion preserves code lines and decodes entities once", () => {
  assert.equal(
    htmlToText("<pre><code>if value:\n    return 1</code></pre>"),
    "if value:\n    return 1",
  );
  assert.equal(htmlToText("<div>one</div><div>two</div>"), "one\ntwo");
  assert.equal(htmlToText("<div>one<br>two</div>"), "one\ntwo");
  assert.equal(htmlToText("x < y && z > 0"), "x < y && z > 0");
  assert.equal(decodeEntitiesFallback("&lt;"), "<");
});

test("line diff aligns equal, missing, extra, and replaced lines", () => {
  const replaced = diffLines("one\ntwo", "one\nchanged");
  const missing = diffLines("one\ntwo", "one");
  const extra = diffLines("one", "one\nextra");

  assert.deepEqual(
    replaced.map((row) => row.type),
    ["equal", "replace"],
  );
  assert.deepEqual(replaced[0], {
    type: "equal",
    expected: "one",
    provided: "one",
    expectedLine: 1,
    providedLine: 1,
  });
  assert.equal(replaced[1].expectedLine, 2);
  assert.equal(replaced[1].providedLine, 2);
  assert.deepEqual(
    missing.map((row) => row.type),
    ["equal", "remove"],
  );
  assert.deepEqual(
    extra.map((row) => row.type),
    ["equal", "add"],
  );
});

test("storage access failures do not stop editor initialization", () => {
  const restrictedWindow = {};
  Object.defineProperty(restrictedWindow, "localStorage", {
    get() {
      throw new Error("Storage access denied");
    },
  });

  assert.equal(getStorage(restrictedWindow, "localStorage"), null);
  assert.equal(getStorage(null, "localStorage"), null);
});

test("answer state from a different card cannot leak into the current diff", () => {
  const staleState = {
    expected: "return old_answer",
    typed: "return old_answer",
    mode: "exact",
  };

  assert.deepEqual(selectAnswerState(staleState, "return current_answer"), {
    expected: "return current_answer",
    mode: "exact",
    typed: "",
  });
  assert.deepEqual(
    selectAnswerState(
      { expected: "return current_answer", typed: "return current_answer" },
      "return current_answer",
    ),
    {
      expected: "return current_answer",
      mode: undefined,
      typed: "return current_answer",
    },
  );
});

test("card templates retain native typing and load the local editor script", () => {
  const front = fs.readFileSync(path.join(cardDir, "front.html"), "utf8");
  const back = fs.readFileSync(path.join(cardDir, "back.html"), "utf8");
  const script = fs.readFileSync(
    path.join(cardDir, "media/_programming-cloze.js"),
    "utf8",
  );

  assert.match(front, /\{\{type:cloze:Text\}\}/);
  assert.match(back, /\{\{type:cloze:Text\}\}/);
  assert.match(front, /data-pc-editor/);
  assert.match(back, /data-pc-answer/);
  assert.match(front, /src="_programming-cloze\.js"/);
  assert.match(back, /src="_programming-cloze\.js"/);
  assert.match(script, /textarea\.id = "typeans"/);
  assert.match(script, /input\.closest\("center"\)/);
  assert.match(script, /data-pc-mode/);
  assert.match(script, /data-pc-whitespace-toggle/);

  for (const [name, template] of [
    ["front.html", front],
    ["back.html", back],
  ]) {
    const ids = [...template.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]);
    assert.equal(new Set(ids).size, ids.length, `${name} contains duplicate ids`);
  }
});
