<script setup lang="ts">
import { computed, inject } from "vue";

import { countChanges } from "../../core/changes";
import { editorStateKey } from "../../core/context/keys";

/*
 * A card header's change summary (core/changes.ts): "New" on an added
 * card; on a closed one, how many fields changed inside. An open card
 * shows nothing: its changed fields carry their own marker.
 */

const props = defineProps<{
  path: string;
  expanded: boolean;
}>();

// Absent outside VulniverseEditor (e.g. a renderer mounted on its own).
const state = inject(editorStateKey, null);

const label = computed(() => {
  if (!state) return null;
  if (state.addedPaths.value.has(props.path)) return "New";
  if (props.expanded || !state.changedPaths.value.has(props.path)) return null;

  const count = countChanges(state.changedPaths.value, props.path);

  return count === 1 ? "1 change" : count ? `${count} changes` : "Changed";
});
</script>

<template>
  <span
    v-if="label"
    class="badge rounded-pill text-bg-info editor-change-badge align-self-center"
    title="Since the last save"
  >{{ label }}</span>
</template>
