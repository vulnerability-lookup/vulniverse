<script setup lang="ts">
/*
 * How many entries a card list has, small and muted after its title.
 * Only for two or more, like "Expand all": an empty list says "No
 * data", and a single card is open anyway.
 */

defineProps<{
  count: number;
}>();
</script>

<template>
  <span
    v-if="count > 1"
    class="editor-list-count"
  ><span aria-hidden="true">{{ count }}</span><span class="visually-hidden">({{ count }} entries)</span></span>
</template>
