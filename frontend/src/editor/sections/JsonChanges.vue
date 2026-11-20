<script setup lang="ts">
import { computed, ref } from "vue";

import { useEditorContext } from "../core/context";
import { diffLines, foldUnchanged } from "../core/line-diff";
import type { DiffLine } from "../core/line-diff";

/*
 * The JSON section's "Changes" view: the record as saved and as edited,
 * formatted the same way, compared line by line. Removed lines are red,
 * added ones blue, like the markers in the form. Long unchanged stretches
 * are folded; a click shows them.
 */

const editor = useEditorContext();

const format = (value: unknown) => (value ? JSON.stringify(value, null, 2).split("\n") : []);

const lines = computed(() => diffLines(format(editor.originalRecord.value), format(editor.record.value)));
const rows = computed(() => foldUnchanged(lines.value));
const counts = computed(() => ({
  added: lines.value.filter((line) => line.kind === "added").length,
  removed: lines.value.filter((line) => line.kind === "removed").length,
}));

// Gaps opened by a click, by the old line number they start at.
const opened = ref(new Set<number>());

function open(lines: DiffLine[]): void {
  opened.value = new Set([...opened.value, lines[0]!.oldNumber!]);
}

const SIGN = { same: " ", added: "+", removed: "−" } as const;
const SPOKEN = { same: "", added: "Added: ", removed: "Removed: " } as const;
</script>

<template>
  <div>
    <p
      v-if="!counts.added && !counts.removed"
      class="text-secondary"
    >
      No unsaved changes: the record is as saved.
    </p>

    <template v-else>
      <p class="small text-secondary mb-2">
        Since the last save:
        <span class="json-diff-count-removed">{{ counts.removed }} {{ counts.removed === 1 ? "line" : "lines" }} removed</span>,
        <span class="json-diff-count-added">{{ counts.added }} added</span>.
        Edits in the JSON editor count once applied.
      </p>

      <div class="json-diff">
        <table>
          <tbody>
            <template
              v-for="(row, index) in rows"
              :key="index"
            >
              <tr
                v-if="row.type === 'gap' && !opened.has(row.lines[0]!.oldNumber!)"
                class="json-diff-gap"
              >
                <td colspan="4">
                  <button
                    type="button"
                    class="btn btn-link btn-sm p-0"
                    @click="open(row.lines)"
                  >
                    Show {{ row.lines.length }} unchanged lines
                  </button>
                </td>
              </tr>
              <template v-else>
                <tr
                  v-for="line in row.type === 'gap' ? row.lines : [row.line]"
                  :key="`${line.oldNumber}-${line.newNumber}`"
                  :class="`json-diff-${line.kind}`"
                >
                  <td class="json-diff-number">
                    {{ line.oldNumber ?? "" }}
                  </td>
                  <td class="json-diff-number">
                    {{ line.newNumber ?? "" }}
                  </td>
                  <td
                    class="json-diff-sign"
                    aria-hidden="true"
                  >
                    {{ SIGN[line.kind] }}
                  </td>
                  <td class="json-diff-text">
                    <span class="visually-hidden">{{ SPOKEN[line.kind] }}</span>{{ line.text }}
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
