<script setup lang="ts">
/*
 * "Expand all" / "Collapse all" in a card list's heading, next to its
 * "+ Add" button (useCollapsibleItems' allExpanded and toggleAll).
 * Only for two cards or more.
 */

defineProps<{
  count: number;
  allExpanded: boolean;
}>();

defineEmits<{
  toggle: [];
}>();
</script>

<template>
  <button
    v-if="count > 1"
    type="button"
    class="btn btn-outline-secondary btn-sm"
    :aria-expanded="allExpanded"
    @click="$emit('toggle')"
  >
    {{ allExpanded ? "Collapse all" : "Expand all" }}
  </button>
</template>
