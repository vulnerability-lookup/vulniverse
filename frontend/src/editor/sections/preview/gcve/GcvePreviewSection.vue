<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  findXGcveOccurrences,
} from "../../../gcve";

import MetadataPreview from
  "../cve/MetadataPreview.vue";

import SourcePreview from
  "../cve/SourcePreview.vue";

import {
  useCvePreview,
} from "../cve/use-cve-preview";

import GcvePreview from
  "./GcvePreview.vue";


const {
  record,

  cveId,
  metadataVulnId,

  state,
  metadataDates,
  assigner,

  sources,
} = useCvePreview();


const gcveOccurrences =
  computed(() => {
    return findXGcveOccurrences(
      record.value,
    );
  });


const gcveVulnId =
  computed<
    string | undefined
  >(() => {
    const value =
      gcveOccurrences.value[0]
        ?.extensions[0]
        ?.vulnId;

    return (
      typeof value === "string"
      && value
    )
      ? value
      : undefined;
  });


const primaryIdentifier =
  computed(() => {
    return (
      gcveVulnId.value
      ?? metadataVulnId.value
      ?? cveId.value
      ?? "Unassigned identifier"
    );
  });


const secondaryIdentifier =
  computed<
    string | undefined
  >(() => {
    return (
      cveId.value
      && cveId.value
        !== primaryIdentifier.value
    )
      ? cveId.value
      : undefined;
  });
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
      :secondary-identifier="
        secondaryIdentifier
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

    <GcvePreview
      :occurrences="
        gcveOccurrences
      "
    />
  </section>
</template>
