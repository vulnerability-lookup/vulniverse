<script setup lang="ts">
import {
  computed,
  nextTick,
  ref,
  watch,
} from "vue";

import {
  useEditorContext,
} from "../core/context";

import type {
  EditorDocument
} from "../contracts";

import JsonChanges from "./JsonChanges.vue";

const editor = useEditorContext();

// "edit" the JSON, or see the "changes" since the last save.
const view = ref<"edit" | "changes">("edit");

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
 * (here, the Discard edits button) rather than typing anything, which makes
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
      parsed as EditorDocument;

    parseError.value = null;
    editor.notice.value = "JSON applied. Save to keep the changes.";
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
      <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
        <h2 class="h4 mb-0">Advanced JSON</h2>

        <div
          class="btn-group btn-group-sm"
          role="group"
          aria-label="View"
        >
          <button
            type="button"
            class="btn"
            :class="view === 'edit' ? 'btn-secondary' : 'btn-outline-secondary'"
            :aria-pressed="view === 'edit'"
            @click="view = 'edit'"
          >
            Edit
          </button>
          <button
            type="button"
            class="btn"
            :class="view === 'changes' ? 'btn-secondary' : 'btn-outline-secondary'"
            :aria-pressed="view === 'changes'"
            @click="view = 'changes'"
          >
            Changes
            <span
              v-if="editor.dirty.value"
              class="editor-changed-dot"
            ><span class="visually-hidden">(has unsaved changes)</span></span>
          </button>
        </div>
      </div>

      <p
        v-if="view === 'edit'"
        class="text-secondary mt-2 mb-0"
      >
        Review or replace the complete record.
        Changes are only applied after pressing
        Apply JSON.
      </p>
    </header>

    <JsonChanges v-if="view === 'changes'" />

    <template v-else>
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
          Discard edits
        </button>

        <button
          type="button"
          class="btn btn-primary"
          @click="apply"
        >
          Apply JSON
        </button>
      </div>
    </template>
  </section>
</template>
