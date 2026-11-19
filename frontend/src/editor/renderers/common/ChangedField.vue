<script setup lang="ts">
import { useIsChanged } from "../../core/changes";

/*
 * Wraps a field a card renders itself (not through GridLayoutRenderer)
 * with the "changed" marker for `path`, so the bar lands on that field
 * rather than on the whole card (core/changes.ts, editor.scss).
 */

defineProps<{
  path: string;
}>();

const isChanged = useIsChanged();
</script>

<template>
  <div
    :data-path="path"
    :class="{ 'editor-changed': isChanged(path) }"
  >
    <slot />

    <span
      v-if="isChanged(path)"
      class="visually-hidden"
    >(changed since the last save)</span>
  </div>
</template>
