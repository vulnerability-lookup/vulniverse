<script setup lang="ts">
import { computed, inject } from "vue";

import { useUndoChange } from "../../core/changes";
import { editorStateKey } from "../../core/context/keys";
import { shownValue } from "../../core/record-tree";

/*
 * Below a list's cards: the items removed from it since the last save
 * (core/changes.ts), each with a button to put it back where it was.
 * Gone after Save, like every other change marker.
 */

const props = defineProps<{
  /** The list's data path, e.g. "containers.cna.references". */
  path: string;
}>();

// Absent outside VulniverseEditor (e.g. a renderer mounted on its own).
const state = inject(editorStateKey, null);
const restore = useUndoChange();

const removed = computed(() => (state?.changes.value ?? []).filter((change) => (
  change.kind === "removed"
  && change.fromList
  && change.path.slice(0, change.path.lastIndexOf(".")) === props.path
)));
</script>

<template>
  <div
    v-for="change in removed"
    :key="change.path"
    class="card mb-2 editor-removed editor-changed"
  >
    <div class="card-body py-2 d-flex align-items-center justify-content-between gap-2">
      <span class="small text-truncate">
        <span class="badge bg-danger-subtle text-danger-emphasis me-2">Removed</span>
        <span class="text-secondary text-decoration-line-through">{{ shownValue(change.before) }}</span>
      </span>

      <button
        type="button"
        class="btn btn-sm btn-outline-primary flex-shrink-0"
        :aria-label="`Restore the removed entry ${shownValue(change.before)}`"
        @click="restore(change)"
      >
        Restore
      </button>
    </div>
  </div>
</template>
