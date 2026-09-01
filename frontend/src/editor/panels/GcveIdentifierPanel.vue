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

/*
 * cveMetadata.vulnId isn't part of the official CVE 5.2.0 schema (only
 * x_gcve[].vulnId is) — this field exists purely for hosts that key
 * their own storage off it. context.record is the editor's live
 * reactive record, not a snapshot, so writing through it here flows
 * straight into dirty-tracking/save like any generated form field.
 */
const vulnId = computed<string>({
  get() {
    return props.context.record.cveMetadata?.vulnId ?? "";
  },
  set(value) {
    /* eslint-disable vue/no-mutating-props */
    props.context.record.cveMetadata ??= {};
    props.context.record.cveMetadata.vulnId = value;
    /* eslint-enable vue/no-mutating-props */
  },
});
</script>

<template>
  <div class="p-3">
    <p class="text-secondary">
      This host stores every record as GCVE. Set the GCVE identifier
      here so this record can be saved.
    </p>

    <div class="mb-3">
      <label
        for="gcve-identifier-input"
        class="form-label"
      >
        GCVE identifier
      </label>

      <input
        id="gcve-identifier-input"
        v-model="vulnId"
        type="text"
        class="form-control"
        placeholder="GCVE-0-2026-00001"
      >
    </div>
  </div>
</template>
