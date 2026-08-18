<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  EditorModuleContext,
} from "../contracts";

const props = defineProps<{
  context: EditorModuleContext;
}>();

const cna = computed(() => {
  return props.context.record.containers?.cna;
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
      Example panel module — demonstrates a module contributing its
      own navigation tab and component, not just a header button.
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
