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

import authoringSchema from
  "@/generated/schemas/cve-5.2.0/authoring.schema.json";

import editorUiSchema from
  "@/generated/schemas/cve-5.2.0/ui.schema.json";

import {
  useEditorContext,
} from "../use-editor-context";

import type {
  VulnerabilityRecord,
} from "../contracts";

const editor = useEditorContext();

const schema = authoringSchema as JsonSchema;
const uiSchema = editorUiSchema as UISchemaElement;

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
