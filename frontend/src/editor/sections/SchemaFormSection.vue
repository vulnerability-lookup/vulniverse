<script setup lang="ts">
import {
  computed,
  shallowRef,
  toRaw,
} from "vue";

import {
  JsonForms,
} from "@jsonforms/vue";

import {
  vanillaRenderers,
} from "@jsonforms/vue-vanilla";

import {
  customRenderers,
} from "../renderers";

import type {
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import cveAuthoringSchema from
  "@/generated/schemas/cve-5.2.0/authoring.schema.json";

import cveUiSchema from
  "@/generated/schemas/cve-5.2.0/ui.schema.json";

import gcveAuthoringSchema from
  "@/generated/schemas/gcve-bcp-05-1.7/authoring.schema.json";

import gcveUiSchema from
  "@/generated/schemas/gcve-bcp-05-1.7/ui.schema.json";

import {
  DEFAULT_PROFILE_ID,
} from "../profiles";

import {
  useEditorContext,
} from "../use-editor-context";

import type {
  VulnerabilityRecord,
} from "../contracts";

const editor = useEditorContext();

/*
 * Vite needs statically-resolvable import paths, so this is a
 * two-entry literal map rather than a profile-keyed dynamic import —
 * appropriate for exactly the two profiles Vulniverse generates
 * schemas for today. Add an entry here (and a matching generated
 * schema pair) if a third profile is ever wired up.
 */
const SCHEMA_PAIRS: Record<
  string,
  { schema: JsonSchema; uiSchema: UISchemaElement }
> = {
  "cve-5.2.0": {
    schema: cveAuthoringSchema as JsonSchema,
    uiSchema: cveUiSchema as UISchemaElement,
  },
  "gcve-bcp-05-1.7": {
    schema: gcveAuthoringSchema as JsonSchema,
    uiSchema: gcveUiSchema as UISchemaElement,
  },
};

const activePair = computed(() => {
  return (
    SCHEMA_PAIRS[editor.profile.value ?? DEFAULT_PROFILE_ID]
    ?? SCHEMA_PAIRS[DEFAULT_PROFILE_ID]!
  );
});

const schema = computed(() => activePair.value.schema);
const uiSchema = computed(() => activePair.value.uiSchema);

const renderers = shallowRef(
  Object.freeze([
    ...customRenderers,
    ...vanillaRenderers,
  ]),
);

const formData = computed(() => {
  /*
   * JsonForms mutates and deep-inspects this object internally
   * (default-value filling, ajv validation). Handing it the Vue
   * reactive Proxy that editor.record.value returns causes every
   * internal read/write to round-trip through Vue's reactivity
   * tracking, which feeds back into onChange and recurses forever.
   * toRaw() gives it the plain underlying object instead.
   */
  return editor.record.value
    ? toRaw(editor.record.value)
    : {};
});

function handleChange(event: {
  data: VulnerabilityRecord;
  errors?: unknown[];
}): void {
  editor.record.value = event.data;
}
</script>

<template>
  <JsonForms
    :data="formData"
    :schema="schema"
    :uischema="uiSchema"
    :renderers="renderers"
    validation-mode="ValidateAndShow"
    @change="handleChange"
  />
</template>
