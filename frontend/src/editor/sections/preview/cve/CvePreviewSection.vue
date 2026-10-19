<script setup lang="ts">
import MetadataPreview from
  "./MetadataPreview.vue";

import SourcePreview from
  "./SourcePreview.vue";

import {
  useCvePreview,
} from "./use-cve-preview";


const {
  primaryIdentifier,
  state,
  metadataDates,
  assigner,
  sources,
} = useCvePreview();
</script>


<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">
        Preview
      </h2>

      <p class="text-secondary">
        A read-only rendering of the
        record as currently edited.
      </p>
    </header>

    <MetadataPreview
      :primary-identifier="
        primaryIdentifier
      "
      :state="state"
      :assigner="assigner"
      :dates="metadataDates"
    />

    <SourcePreview
      v-for="source in sources"
      :key="source.key"
      :source="source"
    />
  </section>
</template>
