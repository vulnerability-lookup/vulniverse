<script setup lang="ts">
import {
  computed,
  nextTick,
  ref,
  watch,
} from "vue";

import {
  useEditorContext,
} from "../use-editor-context";

import type {
  VulnerabilityRecord,
} from "../contracts";

const editor = useEditorContext();

const source = ref("");
const parseError = ref<string | null>(null);

const gutter = ref<HTMLElement | null>(null);
const textarea = ref<HTMLTextAreaElement | null>(null);

/*
 * Line numbers only stay aligned with actual content lines if the
 * textarea never soft-wraps (see the white-space: pre / overflow-x
 * rules below) — otherwise one source line could span several
 * visual rows and the numbering would drift.
 */
const lineNumbers = computed(() => {
  const count = source.value.split("\n").length;

  return Array.from(
    { length: count },
    (_, index) => index + 1,
  ).join("\n");
});

function syncGutterScroll(): void {
  if (gutter.value && textarea.value) {
    gutter.value.scrollTop = textarea.value.scrollTop;
  }
}

const INDENT = "  ";

function setSelectionRange(
  start: number,
  end: number,
): void {
  nextTick(() => {
    textarea.value?.setSelectionRange(start, end);
  });
}

/*
 * A plain textarea treats Tab as "move focus to the next element"
 * (here, the Reset button) rather than typing anything, which makes
 * it unusable for editing indented JSON. This intercepts Tab/Shift+
 * Tab to indent/outdent instead, matching how code editors behave.
 */
function handleTab(
  event: KeyboardEvent,
): void {
  const element = textarea.value;

  if (!element) {
    return;
  }

  event.preventDefault();

  const start = element.selectionStart ?? 0;
  const end = element.selectionEnd ?? 0;
  const value = source.value;
  const lineStart = value.lastIndexOf("\n", start - 1) + 1;

  if (event.shiftKey) {
    const before = value.slice(0, lineStart);
    const selected = value.slice(lineStart, end);
    const after = value.slice(end);

    let firstLineRemoved = 0;
    let totalRemoved = 0;

    const outdented = selected
      .split("\n")
      .map((line, index) => {
        const removable = line.match(/^ {1,2}/)?.[0] ?? "";

        if (index === 0) {
          firstLineRemoved = removable.length;
        }

        totalRemoved += removable.length;

        return line.slice(removable.length);
      })
      .join("\n");

    source.value = before + outdented + after;

    setSelectionRange(
      Math.max(lineStart, start - firstLineRemoved),
      end - totalRemoved,
    );

    return;
  }

  if (start === end) {
    source.value =
      value.slice(0, start) + INDENT + value.slice(end);

    setSelectionRange(
      start + INDENT.length,
      start + INDENT.length,
    );

    return;
  }

  const before = value.slice(0, lineStart);
  const selected = value.slice(lineStart, end);
  const after = value.slice(end);
  const indented = selected.replace(/^/gm, INDENT);

  source.value = before + indented + after;

  setSelectionRange(
    start + INDENT.length,
    end + (indented.length - selected.length),
  );
}

/*
 * Records copied from elsewhere (editors, formatters, other tools)
 * commonly carry a trailing comma before a closing `}`/`]` — valid
 * in a JS object literal, rejected by strict JSON.parse. Stripping
 * those before parsing avoids a wall of confusing syntax errors for
 * otherwise well-formed pasted data. Scans char-by-char tracking
 * string/escape state so a literal ", }" inside a string value is
 * left untouched.
 */
function stripTrailingCommas(
  json: string,
): string {
  let result = "";
  let inString = false;
  let escaped = false;

  for (let index = 0; index < json.length; index += 1) {
    const char = json.charAt(index);

    if (inString) {
      result += char;

      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === "\"") {
        inString = false;
      }

      continue;
    }

    if (char === "\"") {
      inString = true;
      result += char;
      continue;
    }

    if (char === ",") {
      let lookahead = index + 1;

      while (/\s/.test(json.charAt(lookahead))) {
        lookahead += 1;
      }

      if (
        json.charAt(lookahead) === "}"
        || json.charAt(lookahead) === "]"
      ) {
        continue;
      }
    }

    result += char;
  }

  return result;
}

const formattedRecord = computed(() => {
  return JSON.stringify(
    editor.record.value,
    null,
    2,
  );
});

/*
 * Refresh the temporary JSON text whenever the
 * canonical record changes and the user is not
 * currently applying an invalid JSON document.
 */
watch(
  formattedRecord,
  (value) => {
    if (!parseError.value) {
      source.value = value;
    }
  },
  {
    immediate: true,
  },
);

function reset(): void {
  source.value = formattedRecord.value;
  parseError.value = null;
}

function apply(): void {
  try {
    const parsed: unknown =
      JSON.parse(stripTrailingCommas(source.value));

    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      throw new Error(
        "The record must be a JSON object.",
      );
    }

    editor.record.value =
      parsed as VulnerabilityRecord;

    parseError.value = null;
  } catch (error) {
    parseError.value =
      error instanceof Error
        ? error.message
        : "Invalid JSON.";
  }
}
</script>

<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">Advanced JSON</h2>

      <p class="text-secondary">
        Review or replace the complete record.
        Changes are only applied after pressing
        Apply JSON.
      </p>
    </header>

    <div class="json-editor">
      <pre
        ref="gutter"
        class="json-gutter"
        aria-hidden="true"
      >{{ lineNumbers }}</pre>

      <textarea
        ref="textarea"
        v-model="source"
        class="form-control json-source"
        spellcheck="false"
        @scroll="syncGutterScroll"
        @keydown.tab="handleTab"
      />
    </div>

    <p
      v-if="parseError"
      role="alert"
      class="text-danger mt-2"
    >
      {{ parseError }}
    </p>

    <div class="d-flex justify-content-end gap-2 mt-3">
      <button
        type="button"
        class="btn btn-outline-secondary"
        @click="reset"
      >
        Reset
      </button>

      <button
        type="button"
        class="btn btn-primary"
        @click="apply"
      >
        Apply JSON
      </button>
    </div>
  </section>
</template>

<style scoped>
.json-editor {
  display: flex;
  align-items: stretch;
  height: 32rem;
}

.json-gutter,
.json-source {
  font-family:
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Monaco,
    Consolas,
    monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  padding-top: 0.375rem;
  padding-bottom: 0.375rem;
}

.json-gutter {
  margin: 0;
  padding-left: 0.75rem;
  padding-right: 0.5rem;
  height: 100%;
  overflow: hidden;
  white-space: pre;
  text-align: right;
  color: var(--bs-secondary-color);
  background-color: var(--bs-tertiary-bg);
  border: var(--bs-border-width) solid var(--bs-border-color);
  border-right: 0;
  border-top-left-radius: var(--bs-border-radius);
  border-bottom-left-radius: var(--bs-border-radius);
  user-select: none;
  flex-shrink: 0;
}

.json-source {
  height: 100%;
  white-space: pre;
  overflow-wrap: normal;
  overflow-x: auto;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  flex: 1 1 auto;
  resize: none;
}
</style>
