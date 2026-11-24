import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const sourceDir = path.resolve(testDir, "../source");
const { evalCond, generateRandoms, calculate } = await import(
  path.join(sourceDir, "js/random-math.js")
);

class NumberValue {
  constructor(value) {
    this.value = Number(value);
  }

  text() {
    return String(this.value);
  }

  toTeX() {
    return String(this.value);
  }

  eq(other) {
    return this.value === other.value;
  }

  lt(other) {
    return this.value < other.value;
  }

  lte(other) {
    return this.value <= other.value;
  }

  gt(other) {
    return this.value > other.value;
  }

  gte(other) {
    return this.value >= other.value;
  }
}

function nerdamer(expression) {
  if (expression instanceof NumberValue) {
    return expression;
  }
  const compact = String(expression).replace(/\s/g, "");
  if (compact.includes("*")) {
    const parts = compact.split("*").map((part) =>
      Number(part.replace(/[()]/g, "")),
    );
    return new NumberValue(parts[0] * parts[1]);
  }
  return new NumberValue(Number(compact.replace(/[()]/g, "")));
}

globalThis.nerdamer = nerdamer;
globalThis.functionPlot = () => {};

test("random bounds include min and max", () => {
  const originalRandom = Math.random;
  const originalSeedrandom = Math.seedrandom;
  Math.seedrandom = () => {};
  globalThis.Persistence = { isAvailable: () => false };

  try {
    const calc = { textContent: "num = r(1, 100);" };
    globalThis.document = { getElementById: () => calc };

    Math.random = () => 0;
    generateRandoms();
    assert.equal(calc.textContent, "num=1;");

    calc.textContent = "num = r(1, 100);";
    Math.random = () => 0.999999999;
    generateRandoms();
    assert.equal(calc.textContent, "num=100;");
  } finally {
    Math.random = originalRandom;
    Math.seedrandom = originalSeedrandom;
  }
});

test("comparison operators dispatch to the right branch", () => {
  const variables = { $x: new NumberValue(5) };
  assert.equal(evalCond("$x lt 6", variables), true);
  assert.equal(evalCond("$x lte 5", variables), true);
  assert.equal(evalCond("$x gt 4", variables), true);
  assert.equal(evalCond("$x gte 5", variables), true);
  assert.equal(evalCond("$x eq 5", variables), true);
  assert.equal(evalCond("$x eq 4", variables), false);
  assert.equal(evalCond("not $x lt 4", variables), true);
});

test("calculate produces the correct square", () => {
  const calc = { textContent: "num = 4;" };
  const sub = { innerHTML: "Square: ${$num * $num}" };
  globalThis.document = {
    getElementById: (id) => (id === "calc" ? calc : sub),
  };
  calculate();
  assert.equal(sub.innerHTML, "Square: 16");
});

test("front and back templates preserve the generated value", () => {
  const store = new Map();
  const persistence = {
    isAvailable: () => true,
    setItem: (value) => store.set("value", value),
    getItem: () => store.get("value"),
  };
  globalThis.Persistence = persistence;

  const originalRandom = Math.random;
  Math.random = () => 0.249;
  try {
    const calc = { textContent: "num = r(1, 100);" };
    globalThis.document = { getElementById: () => calc };
    generateRandoms();
    persistence.setItem(calc.textContent);

    calc.textContent = "num = r(1, 100);";
    calc.textContent = persistence.getItem();
    assert.equal(calc.textContent, "num=25;");
  } finally {
    Math.random = originalRandom;
  }

  const front = fs.readFileSync(path.join(sourceDir, "front.html"), "utf8");
  const back = fs.readFileSync(path.join(sourceDir, "back.html"), "utf8");
  assert.match(front, /Persistence\.setItem/);
  assert.match(back, /Persistence\.getItem/);
  assert.doesNotMatch(back, /createGraphs\s*\(/);
});
