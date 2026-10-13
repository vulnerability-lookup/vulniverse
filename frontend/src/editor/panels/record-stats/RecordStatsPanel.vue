<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  CveRecord,
  EditorContext,
} from "../../contracts";

const props = defineProps<{
  context: EditorContext;
}>();

/*
 * This example panel is CVE/GCVE-shaped (reads containers.cna
 * directly) — safe only because it's always used against one of
 * those two profiles today. A future non-CVE-shaped profile adding
 * this panel would need its own stats panel instead.
 */
const cna = computed(() => {
  return (props.context.record as CveRecord).containers?.cna;
});

const descriptionsCount = computed(() => {
  return cna.value?.descriptions?.length ?? 0;
});

const affectedCount = computed(() => {
  return cna.value?.affected?.length ?? 0;
});

const referencesCount = computed(() => {
  return cna.value?.references?.length ?? 0;
});
</script>

<template>
  <div class="p-3">
    <p class="text-secondary">
      Example panel module
    </p>

    <dl class="row">
      <dt class="col-sm-3">Identifier</dt>
      <dd class="col-sm-9">{{ context.identifier || "(unsaved)" }}</dd>

      <dt class="col-sm-3">Profile</dt>
      <dd class="col-sm-9">{{ context.profile }}</dd>

      <dt class="col-sm-3">Descriptions</dt>
      <dd class="col-sm-9">{{ descriptionsCount }}</dd>

      <dt class="col-sm-3">Affected products</dt>
      <dd class="col-sm-9">{{ affectedCount }}</dd>

      <dt class="col-sm-3">References</dt>
      <dd class="col-sm-9">{{ referencesCount }}</dd>
    </dl>
  </div>
</template>
