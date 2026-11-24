(function (root, factory) {
  const api = factory();

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }

  if (root) {
    root.ProgrammingCloze = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const MODES = Object.freeze({
    EXACT: "exact",
    INDENT: "indent",
    LOOSE: "loose",
  });

  const MODE_LABELS = Object.freeze({
    [MODES.EXACT]: "Exact whitespace",
    [MODES.INDENT]: "Ignore indentation",
    [MODES.LOOSE]: "Ignore all whitespace",
  });

  const MODE_STORAGE_KEY = "programming-cloze:comparison-mode";
  const STATE_STORAGE_KEY = "programming-cloze:last-answer";
  const INDENT = "  ";
  const STRUCTURAL_NEWLINE = "\uE000";

  const BLOCK_ELEMENTS = new Set([
    "address",
    "article",
    "aside",
    "blockquote",
    "caption",
    "col",
    "colgroup",
    "dd",
    "details",
    "dialog",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hgroup",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
  ]);

  const HTML_ENTITIES = Object.freeze({
    amp: "&",
    apos: "'",
    gt: ">",
    lt: "<",
    nbsp: "\u00a0",
    quot: '"',
  });

  function normalizeLineEndings(text) {
    return String(text ?? "").replace(/\r\n?/g, "\n");
  }

  function normalizeExact(text) {
    return normalizeLineEndings(text);
  }

  function normalizeIndent(text) {
    return normalizeExact(text)
      .split("\n")
      .map((line) => line.replace(/^[\t ]+/, ""))
      .join("\n");
  }

  function normalizeLoose(text) {
    return normalizeExact(text).replace(/\s+/g, "");
  }

  function normalizeForMode(text, mode) {
    switch (mode) {
      case MODES.INDENT:
        return normalizeIndent(text);
      case MODES.LOOSE:
        return normalizeLoose(text);
      case MODES.EXACT:
      default:
        return normalizeExact(text);
    }
  }

  function compareText(expected, provided, mode = MODES.EXACT) {
    const exactExpected = normalizeExact(expected);
    const exactProvided = normalizeExact(provided);
    const normalizedExpected = normalizeForMode(expected, mode);
    const normalizedProvided = normalizeForMode(provided, mode);
    const exactMatches = exactExpected === exactProvided;

    return {
      mode,
      exactMatches,
      matches: normalizedExpected === normalizedProvided,
      whitespaceOnly:
        !exactMatches &&
        normalizeLoose(expected) === normalizeLoose(provided),
      normalizedExpected,
      normalizedProvided,
    };
  }

  function decodeNumericEntity(entity) {
    const hexadecimal = /^#x/i.test(entity);
    const digits = hexadecimal ? entity.slice(2) : entity.slice(1);
    const codePoint = Number.parseInt(digits, hexadecimal ? 16 : 10);

    if (!Number.isFinite(codePoint) || codePoint < 0) {
      return null;
    }

    try {
      return String.fromCodePoint(codePoint);
    } catch (_error) {
      return null;
    }
  }

  function decodeEntitiesFallback(html) {
    return String(html ?? "").replace(
      /&(#x[0-9a-f]+|#\d+|[a-z][a-z0-9]+);/gi,
      (match, entity) => {
        if (entity.startsWith("#")) {
          return decodeNumericEntity(entity) ?? match;
        }

        const named = HTML_ENTITIES[entity.toLowerCase()];
        return named ?? match;
      },
    );
  }

  function stripFallbackTags(html) {
    const source = String(html ?? "");
    const closingBlockPattern =
      /<\/(?:address|article|aside|blockquote|caption|colgroup|dd|details|dialog|div|dl|dt|fieldset|figcaption|figure|footer|form|h[1-6]|header|hgroup|li|main|nav|ol|p|pre|section|summary|table|tbody|td|tfoot|th|thead|tr|ul)\s*>/gi;
    const standaloneBlockPattern =
      /<(?:hr|col)(?:\s[^>]*)?>/gi;

    return source
      .replace(/<br\s*\/?\s*>/gi, "\n")
      .replace(closingBlockPattern, STRUCTURAL_NEWLINE)
      .replace(standaloneBlockPattern, STRUCTURAL_NEWLINE)
      .replace(/<\/?[a-z][^>]*>|<![^>]*>|<\?[^>]*>/gi, "");
  }

  function htmlToTextFallback(html) {
    const stripped = stripFallbackTags(html);
    const decoded = decodeEntitiesFallback(stripped);
    const withoutBoundaryRuns = decoded.replace(
      new RegExp(`${STRUCTURAL_NEWLINE}+`, "g"),
      STRUCTURAL_NEWLINE,
    );
    const withoutOuterBoundaries = withoutBoundaryRuns
      .replace(new RegExp(`^${STRUCTURAL_NEWLINE}+`), "")
      .replace(new RegExp(`${STRUCTURAL_NEWLINE}+$`), "");

    return normalizeExact(withoutOuterBoundaries.replaceAll(STRUCTURAL_NEWLINE, "\n"));
  }

  function appendStructuralNewline(tokens) {
    const previous = tokens[tokens.length - 1];
    if (previous && previous.structural) {
      return;
    }

    tokens.push({ text: "\n", structural: true });
  }

  function domNodeToText(node, tokens) {
    if (!node) {
      return;
    }

    if (node.nodeType === 3) {
      tokens.push({ text: node.nodeValue || "", structural: false });
      return;
    }

    if (node.nodeType !== 1) {
      return;
    }

    const tagName = String(node.tagName || "").toLowerCase();
    if (["script", "style", "noscript", "template"].includes(tagName)) {
      return;
    }

    if (tagName === "br") {
      tokens.push({ text: "\n", structural: false });
      return;
    }

    const isBlock = BLOCK_ELEMENTS.has(tagName);
    if (isBlock) {
      appendStructuralNewline(tokens);
    }

    node.childNodes.forEach((childNode) => domNodeToText(childNode, tokens));

    if (isBlock) {
      appendStructuralNewline(tokens);
    }
  }

  function htmlToText(html) {
    const source = String(html ?? "");

    if (typeof document === "undefined") {
      return htmlToTextFallback(source);
    }

    const template = document.createElement("template");
    template.innerHTML = source;
    const tokens = [];

    template.content.childNodes.forEach((node) => domNodeToText(node, tokens));

    while (tokens[0]?.structural) {
      tokens.shift();
    }
    while (tokens[tokens.length - 1]?.structural) {
      tokens.pop();
    }

    return normalizeExact(
      tokens.map((token) => token.text).join(""),
    );
  }

  function findPrompt(root) {
    if (!root || typeof root.querySelector !== "function") {
      return null;
    }

    return root.querySelector("[data-pc-prompt]") || root;
  }

  function extractExpectedAnswer(root) {
    if (!root || typeof root.querySelector !== "function") {
      return "";
    }

    const prompt = findPrompt(root);
    const hiddenAnswer = prompt.querySelector(".cloze[data-cloze]");
    if (hiddenAnswer) {
      return htmlToText(hiddenAnswer.getAttribute("data-cloze") || "");
    }

    const visibleAnswer = prompt.querySelector(".cloze[data-ordinal]");
    if (visibleAnswer) {
      return htmlToText(visibleAnswer.innerHTML);
    }

    return "";
  }

  function mergeDiffOperations(operations) {
    const merged = [];

    for (const operation of operations) {
      const previous = merged[merged.length - 1];

      if (
        previous &&
        ((previous.type === "remove" && operation.type === "add") ||
          (previous.type === "add" && operation.type === "remove"))
      ) {
        merged[merged.length - 1] = {
          type: "replace",
          expected: previous.expected,
          provided: operation.provided,
        };
        continue;
      }

      merged.push(operation);
    }

    return merged;
  }

  function diffLines(expected, provided) {
    const expectedLines = normalizeExact(expected).split("\n");
    const providedLines = normalizeExact(provided).split("\n");
    const table = Array.from({ length: expectedLines.length + 1 }, () =>
      Array(providedLines.length + 1).fill(0),
    );

    for (let expectedIndex = expectedLines.length - 1; expectedIndex >= 0; expectedIndex -= 1) {
      for (let providedIndex = providedLines.length - 1; providedIndex >= 0; providedIndex -= 1) {
        table[expectedIndex][providedIndex] =
          expectedLines[expectedIndex] === providedLines[providedIndex]
            ? table[expectedIndex + 1][providedIndex + 1] + 1
            : Math.max(
                table[expectedIndex + 1][providedIndex],
                table[expectedIndex][providedIndex + 1],
              );
      }
    }

    const operations = [];
    let expectedIndex = 0;
    let providedIndex = 0;

    while (
      expectedIndex < expectedLines.length ||
      providedIndex < providedLines.length
    ) {
      if (
        expectedIndex < expectedLines.length &&
        providedIndex < providedLines.length &&
        expectedLines[expectedIndex] === providedLines[providedIndex]
      ) {
        operations.push({
          type: "equal",
          expected: expectedLines[expectedIndex],
          provided: providedLines[providedIndex],
        });
        expectedIndex += 1;
        providedIndex += 1;
      } else if (
        expectedIndex < expectedLines.length &&
        (providedIndex === providedLines.length ||
          table[expectedIndex + 1][providedIndex] >=
            table[expectedIndex][providedIndex + 1])
      ) {
        operations.push({
          type: "remove",
          expected: expectedLines[expectedIndex],
          provided: null,
        });
        expectedIndex += 1;
      } else {
        operations.push({
          type: "add",
          expected: null,
          provided: providedLines[providedIndex],
        });
        providedIndex += 1;
      }
    }

    let expectedLine = 1;
    let providedLine = 1;

    return mergeDiffOperations(operations).map((operation) => {
      const row = { ...operation };

      if (operation.expected !== null) {
        row.expectedLine = expectedLine;
        expectedLine += 1;
      }
      if (operation.provided !== null) {
        row.providedLine = providedLine;
        providedLine += 1;
      }

      return row;
    });
  }

  function getStorage(windowObject, property) {
    try {
      return windowObject?.[property] ?? null;
    } catch (_error) {
      return null;
    }
  }

  function getStoredMode(storage) {
    try {
      const stored = storage?.getItem(MODE_STORAGE_KEY);
      if (Object.values(MODES).includes(stored)) {
        return stored;
      }
    } catch (_error) {
      // Storage can be unavailable in restricted webviews.
    }

    return MODES.INDENT;
  }

  function storeMode(mode, storage) {
    try {
      storage?.setItem(MODE_STORAGE_KEY, mode);
    } catch (_error) {
      // The editor still works when persistence is unavailable.
    }
  }

  function saveAnswerState(state, storage) {
    try {
      storage?.setItem(STATE_STORAGE_KEY, JSON.stringify(state));
    } catch (_error) {
      // The in-memory state remains available to the answer template.
    }
  }

  function loadAnswerState(storage) {
    try {
      const stored = storage?.getItem(STATE_STORAGE_KEY);
      const parsed = stored ? JSON.parse(stored) : null;
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_error) {
      return null;
    }
  }

  function describeResult(result, hasAnswer) {
    if (!hasAnswer) {
      return {
        tone: "neutral",
        label: "Waiting for an answer",
        detail: "Type the code in the editor.",
      };
    }

    if (result.matches) {
      return {
        tone: "good",
        label:
          result.mode === MODES.EXACT
            ? "Exact match"
            : "Match under the selected comparison",
        detail: MODE_LABELS[result.mode],
      };
    }

    if (result.whitespaceOnly) {
      return {
        tone: "warning",
        label: "Whitespace differs",
        detail: "The answer matches when all whitespace is ignored.",
      };
    }

    return {
      tone: "bad",
      label: "Answer does not match",
      detail: `Compared using ${MODE_LABELS[result.mode].toLowerCase()}.`,
    };
  }

  function revealAnswer() {
    if (typeof window !== "undefined" && typeof window.pycmd === "function") {
      window.pycmd("ans");
    }
  }

  function dispatchInput(textarea) {
    const view = textarea.ownerDocument.defaultView;
    const EventConstructor = view?.Event || (typeof Event !== "undefined" ? Event : null);
    if (EventConstructor) {
      textarea.dispatchEvent(new EventConstructor("input", { bubbles: true }));
    }
  }

  function insertText(textarea, text) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    textarea.setRangeText(text, start, end, "end");
    dispatchInput(textarea);
  }

  function selectedLineBounds(textarea) {
    const value = textarea.value;
    const selectionStart = textarea.selectionStart;
    const selectionEnd = textarea.selectionEnd;
    const hasSelection = selectionEnd > selectionStart;
    const lineStart = value.lastIndexOf("\n", selectionStart - 1) + 1;
    let affectedEnd;

    if (!hasSelection) {
      const nextLine = value.indexOf("\n", selectionEnd);
      affectedEnd = nextLine === -1 ? value.length : nextLine;
    } else if (value[selectionEnd - 1] === "\n") {
      affectedEnd = selectionEnd - 1;
    } else {
      const nextLine = value.indexOf("\n", selectionEnd);
      affectedEnd = nextLine === -1 ? value.length : nextLine;
    }

    return {
      affectedEnd,
      hasSelection,
      lineStart,
      selectionEnd,
      selectionStart,
    };
  }

  function indentSelection(textarea) {
    const {
      affectedEnd,
      hasSelection,
      lineStart,
      selectionEnd,
      selectionStart,
    } = selectedLineBounds(textarea);

    if (!hasSelection) {
      insertText(textarea, INDENT);
      return;
    }

    const original = textarea.value.slice(lineStart, affectedEnd);
    const lines = original.split("\n");
    const replacement = lines
      .map((line) => (line.length > 0 ? `${INDENT}${line}` : line))
      .join("\n");
    const startPrefix = replacement.slice(
      0,
      Math.min(selectionStart - lineStart, original.length),
    );
    const endPrefix = replacement.slice(
      0,
      Math.min(selectionEnd - lineStart, original.length),
    );

    textarea.setRangeText(replacement, lineStart, affectedEnd, "select");
    textarea.selectionStart = lineStart + startPrefix.length;
    textarea.selectionEnd = lineStart + endPrefix.length;
    dispatchInput(textarea);
  }

  function outdentSelection(textarea) {
    const { lineStart, affectedEnd, selectionStart, selectionEnd } =
      selectedLineBounds(textarea);

    if (lineStart === affectedEnd) {
      return;
    }

    const original = textarea.value.slice(lineStart, affectedEnd);
    const lines = original.split("\n");
    const removedPerLine = lines.map((line) => {
      const match = line.match(/^(?: {1,2}|\t)/);
      return match ? match[0].length : 0;
    });
    const replacement = lines
      .map((line, index) => line.slice(removedPerLine[index]))
      .join("\n");

    function adjustedOffset(offset) {
      const relative = Math.max(0, Math.min(offset - lineStart, original.length));
      let sourceLine = 0;
      let sourceOffset = 0;

      for (let index = 0; index < lines.length; index += 1) {
        const lineLength = lines[index].length;
        if (relative <= sourceOffset + lineLength) {
          sourceLine = index;
          sourceOffset = relative - sourceOffset;
          break;
        }
        sourceOffset += lineLength + 1;
        sourceLine = index + 1;
      }

      const removedBefore =
        removedPerLine
          .slice(0, sourceLine)
          .reduce((total, removed) => total + removed, 0) +
        Math.min(removedPerLine[sourceLine] || 0, sourceOffset);
      return Math.max(0, relative - removedBefore);
    }

    textarea.setRangeText(replacement, lineStart, affectedEnd, "select");
    textarea.selectionStart = lineStart + adjustedOffset(selectionStart);
    textarea.selectionEnd = lineStart + adjustedOffset(selectionEnd);
    dispatchInput(textarea);
  }

  function createDiffCell(side, lineNumber, text) {
    const cell = document.createElement("div");
    cell.className = `pc-diff-cell pc-diff-${side}`;

    const number = document.createElement("span");
    number.className = "pc-diff-number";
    number.textContent = lineNumber === null ? "" : String(lineNumber);

    const code = document.createElement("code");
    code.textContent = text ?? "";

    cell.append(number, code);
    return cell;
  }

  function renderDiff(container, expected, provided) {
    if (!container) {
      return;
    }

    container.replaceChildren();
    const rows = diffLines(expected, provided);

    if (rows.length === 0) {
      const empty = document.createElement("p");
      empty.className = "pc-diff-empty";
      empty.textContent = "No answer text is available.";
      container.append(empty);
      return;
    }

    rows.forEach((row) => {
      const rowNode = document.createElement("div");
      rowNode.className = `pc-diff-row is-${row.type}`;
      rowNode.append(
        createDiffCell("expected", row.expectedLine, row.expected),
        createDiffCell("provided", row.providedLine, row.provided),
      );
      container.append(rowNode);
    });
  }

  function setupEditor(root) {
    const input = root.querySelector("input#typeans");
    if (!input) {
      root.dataset.pcError = "missing-typeans";
      return;
    }

    const textarea = document.createElement("textarea");
    textarea.id = "typeans";
    textarea.name = input.name;
    textarea.className = "pc-code-input";
    textarea.value = input.value;
    textarea.rows = 8;
    textarea.wrap = "off";
    textarea.spellcheck = false;
    textarea.autocapitalize = "off";
    textarea.autocomplete = "off";
    textarea.setAttribute("autocorrect", "off");
    textarea.setAttribute(
      "aria-label",
      "Type the missing code. Use Control or Command plus Enter to reveal the answer.",
    );
    const centeredInput = input.closest("center");
    if (centeredInput) {
      centeredInput.replaceWith(textarea);
    } else {
      input.replaceWith(textarea);
    }

    const overlay = root.querySelector("[data-pc-overlay]");
    const gutter = root.querySelector("[data-pc-gutter]");
    const metrics = root.querySelector("[data-pc-metrics]");
    const status = root.querySelector("[data-pc-status]");
    const statusDetail = root.querySelector("[data-pc-status-detail]");
    const whitespaceToggle = root.querySelector("[data-pc-whitespace-toggle]");
    const revealButton = root.querySelector("[data-pc-reveal]");
    const modeButtons = Array.from(root.querySelectorAll("[data-pc-mode]"));
    const windowObject = root.ownerDocument.defaultView;
    const storage = getStorage(windowObject, "localStorage");
    const sessionStorage = getStorage(windowObject, "sessionStorage");

    const state = {
      typed: textarea.value,
      expected: extractExpectedAnswer(root),
      mode: getStoredMode(storage),
    };
    windowObject.__programmingClozeState = state;
    saveAnswerState(state, sessionStorage);

    function setMode(mode) {
      if (!Object.values(MODES).includes(mode)) {
        return;
      }

      state.mode = mode;
      storeMode(mode, storage);
      modeButtons.forEach((button) => {
        button.setAttribute(
          "aria-pressed",
          button.dataset.pcMode === mode ? "true" : "false",
        );
      });
      update();
    }

    function updateStatus() {
      const hasAnswer = state.typed.length > 0;
      const result = compareText(state.expected, state.typed, state.mode);
      const description = describeResult(result, hasAnswer);

      if (status) {
        status.textContent = description.label;
        status.dataset.tone = description.tone;
      }
      if (statusDetail) {
        statusDetail.textContent = description.detail;
      }

      return result;
    }

    function visualizeWhitespace(text) {
      return text
        .replace(/ /g, "·")
        .replace(/\t/g, "→   ")
        .replace(/\u00a0/g, "⍽");
    }

    function updateEditorMetrics() {
      const lineCount = Math.max(1, state.typed.split("\n").length);
      if (gutter) {
        gutter.textContent = Array.from(
          { length: lineCount },
          (_, index) => String(index + 1),
        ).join("\n");
      }
      if (metrics) {
        metrics.textContent = `${lineCount} ${
          lineCount === 1 ? "line" : "lines"
        }`;
      }
    }

    function resizeEditor() {
      const viewportHeight = windowObject?.innerHeight || 800;
      const maximumHeight = Math.max(220, Math.min(460, viewportHeight * 0.58));
      const minimumHeight = Math.min(180, maximumHeight);
      textarea.style.height = "auto";
      const nextHeight = Math.min(
        maximumHeight,
        Math.max(minimumHeight, textarea.scrollHeight || minimumHeight),
      );
      textarea.style.height = `${nextHeight}px`;
    }

    function syncScroll() {
      if (overlay) {
        overlay.scrollTop = textarea.scrollTop;
        overlay.scrollLeft = textarea.scrollLeft;
      }
      if (gutter) {
        gutter.scrollTop = textarea.scrollTop;
      }
    }

    function update() {
      state.typed = textarea.value;
      if (overlay) {
        overlay.textContent = visualizeWhitespace(state.typed);
      }
      updateEditorMetrics();
      updateStatus();
      resizeEditor();
      saveAnswerState(state, sessionStorage);
    }

    textarea.addEventListener("input", update);
    textarea.addEventListener("scroll", syncScroll);
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Tab") {
        event.preventDefault();
        event.stopPropagation();
        if (event.shiftKey) {
          outdentSelection(textarea);
        } else {
          indentSelection(textarea);
        }
        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();
        event.stopPropagation();
        if (event.ctrlKey || event.metaKey || event.altKey) {
          revealAnswer();
        } else {
          insertText(textarea, "\n");
        }
      }
    });

    modeButtons.forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.pcMode));
    });

    if (whitespaceToggle) {
      whitespaceToggle.addEventListener("click", () => {
        const visible = root.classList.toggle("pc-show-whitespace");
        whitespaceToggle.setAttribute("aria-pressed", visible ? "true" : "false");
        whitespaceToggle.textContent = visible
          ? "Whitespace: visible"
          : "Whitespace: hidden";
      });
    }

    if (revealButton) {
      revealButton.addEventListener("click", revealAnswer);
    }

    windowObject?.addEventListener("resize", resizeEditor);
    setMode(state.mode);
    update();
    textarea.focus();
    root.dataset.pcReady = "true";
  }

  function selectAnswerState(state, currentExpected) {
    const candidate = state && typeof state === "object" ? state : {};
    const expected = currentExpected || candidate.expected || "";
    const stateMatches =
      !currentExpected || candidate.expected === currentExpected;

    return {
      expected,
      mode: candidate.mode,
      typed: stateMatches ? candidate.typed || "" : "",
    };
  }

  function setupAnswer(root) {
    const windowObject = root.ownerDocument.defaultView;
    const storedState = loadAnswerState(
      getStorage(windowObject, "sessionStorage"),
    );
    const liveState = windowObject?.__programmingClozeState;
    const currentExpected = extractExpectedAnswer(root);
    const state = selectAnswerState(
      liveState && typeof liveState === "object" ? liveState : storedState,
      currentExpected,
    );
    const expected = state.expected;
    const provided = state.typed;
    const mode = Object.values(MODES).includes(state.mode)
      ? state.mode
      : getStoredMode(getStorage(windowObject, "localStorage"));
    const result = compareText(expected, provided, mode);
    const description = describeResult(result, provided.length > 0);

    const status = root.querySelector("[data-pc-status]");
    const statusDetail = root.querySelector("[data-pc-status-detail]");
    const modeLabel = root.querySelector("[data-pc-mode-label]");
    const resultPanel = root.querySelector("[data-pc-result]");
    const diff = root.querySelector("[data-pc-diff]");

    if (status) {
      status.textContent = description.label;
      status.dataset.tone = description.tone;
    }
    if (statusDetail) {
      statusDetail.textContent = provided.length
        ? description.detail
        : "No answer was entered before revealing the solution.";
    }
    if (modeLabel) {
      modeLabel.textContent = MODE_LABELS[mode];
    }
    if (resultPanel) {
      resultPanel.dataset.tone = description.tone;
    }

    renderDiff(diff, expected, provided);
    root.dataset.pcReady = "true";
  }

  function initialize() {
    if (typeof document === "undefined") {
      return;
    }

    const editor = document.querySelector("[data-pc-editor]");
    if (editor) {
      setupEditor(editor);
    }

    const answer = document.querySelector("[data-pc-answer]");
    if (answer) {
      setupAnswer(answer);
    }
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
      initialize();
    }
  }

  return Object.freeze({
    MODES,
    MODE_LABELS,
    compareText,
    decodeEntitiesFallback,
    diffLines,
    extractExpectedAnswer,
    getStorage,
    htmlToText,
    normalizeExact,
    normalizeForMode,
    normalizeIndent,
    normalizeLineEndings,
    normalizeLoose,
    selectAnswerState,
  });
});
