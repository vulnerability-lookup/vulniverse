<script setup lang="ts">
import { computed, inject, ref } from "vue";

import { useUndoChange } from "../core/changes";
import type { RecordChange } from "../core/changes";
import { editorStateKey } from "../core/context/keys";
import { humanize, shownValue as shown, summaryOf } from "../core/record-tree";

/*
 * The header's "unsaved changes" badge, opening the list of what changed
 * since the last save (core/changes.ts): each change with its old and new
 * value, a button to show it in the editor and one to undo just it.
 */

const state = inject(editorStateKey)!;

const open = ref(false);
const menu = ref<HTMLElement | null>(null);
const changes = computed(() => state.changes.value);

// Records are plain JSON, but after form edits they hold nested Vue
// proxies, which structuredClone (even after toRaw) can't copy.
function plainCopy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function valueAt(record: unknown, keys: string[]): unknown {
  return keys.reduce<unknown>(
    (value, key) => (typeof value === "object" && value !== null
      ? (value as Record<string, unknown>)[key]
      : undefined),
    record,
  );
}

/** "Affected › vulnerability-lookup › Repo": list items by what they are. */
function label(change: RecordChange): string {
  // A removed item is only in the saved record.
  const record = change.kind === "removed" ? state.originalRecord.value : state.record.value;
  const keys = change.path.split(".");
  const skip = keys[0] === "containers" && keys[1] === "cna" ? 2 : 0;

  return keys.slice(skip).map((key, index) => {
    if (!/^\d+$/.test(key)) return humanize(key);

    return summaryOf(valueAt(record, keys.slice(0, skip + index + 1))) || `#${Number(key) + 1}`;
  }).join(" › ");
}

// A removed item isn't in the editor any more: show the list it was in.
function revealTarget(change: RecordChange): string {
  return change.kind === "removed" ? change.path.slice(0, change.path.lastIndexOf(".")) : change.path;
}

function show(change: RecordChange): void {
  open.value = false;
  state.revealPath(revealTarget(change));
}

const undoChange = useUndoChange();

function undo(change: RecordChange): void {
  // Its button goes away with the change: keep the focus (and the list open).
  menu.value?.focus();
  undoChange(change);
}

function undoAll(): void {
  if (!state.originalRecord.value || !window.confirm("Undo all unsaved changes?")) return;

  open.value = false;
  state.record.value = plainCopy(state.originalRecord.value);
}

// Focus leaving the list (Tab away, click elsewhere) closes it.
function closeOnLeave(event: FocusEvent): void {
  if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) {
    open.value = false;
  }
}

const title = computed(() => {
  const count = changes.value.length;
  return count ? `${count} unsaved ${count === 1 ? "change" : "changes"}` : "Unsaved changes";
});
</script>

<template>
  <div
    class="dropdown d-inline-block"
    @focusout="closeOnLeave"
    @keydown.esc="open = false"
  >
    <button
      type="button"
      class="badge bg-info-subtle text-info-emphasis border border-info-subtle editor-unsaved-toggle"
      aria-haspopup="dialog"
      :aria-expanded="open"
      title="Show what changed since the last save"
      @click="open = !open"
    >
      {{ title }} ▾
    </button>

    <div
      v-if="open"
      ref="menu"
      tabindex="-1"
      class="dropdown-menu show p-0 editor-changes-menu"
      role="dialog"
      aria-label="Unsaved changes"
    >
      <div class="d-flex justify-content-between align-items-center px-3 py-2 border-bottom">
        <span class="fw-semibold small">Changed since the last save</span>
        <button
          type="button"
          class="btn btn-sm btn-outline-danger"
          @click="undoAll"
        >
          Undo all
        </button>
      </div>

      <p
        v-if="!changes.length"
        class="small text-secondary px-3 py-2 mb-0"
      >
        No field changed, only the order of fields in the record.
      </p>

      <ul
        v-else
        class="list-group list-group-flush editor-changes-list"
      >
        <li
          v-for="change in changes"
          :key="`${change.kind}:${change.path}`"
          class="list-group-item d-flex align-items-start gap-2"
        >
          <div class="flex-grow-1 small editor-changes-text">
            <div
              class="fw-semibold text-truncate"
              :title="change.path"
            >
              {{ label(change) }}
            </div>

            <div
              v-if="change.kind === 'added'"
              class="text-truncate"
            >
              <span class="badge text-bg-info me-1">New</span>{{ shown(change.after) }}
            </div>
            <div
              v-else-if="change.kind === 'removed'"
              class="text-truncate"
            >
              <span class="badge bg-danger-subtle text-danger-emphasis me-1">Removed</span>{{ shown(change.before) }}
            </div>
            <template v-else>
              <div
                class="text-truncate text-secondary text-decoration-line-through"
                :title="`Saved: ${shown(change.before)}`"
              >
                {{ shown(change.before) }}
              </div>
              <div
                class="text-truncate"
                :title="`Now: ${shown(change.after)}`"
              >
                {{ shown(change.after) }}
              </div>
            </template>
          </div>

          <div class="d-flex gap-1 flex-shrink-0">
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              :aria-label="`Show ${label(change)} in the editor`"
              @click="show(change)"
            >
              Show
            </button>
            <button
              type="button"
              class="btn btn-sm btn-outline-primary"
              :aria-label="`Undo the change to ${label(change)}`"
              @click="undo(change)"
            >
              Undo
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
