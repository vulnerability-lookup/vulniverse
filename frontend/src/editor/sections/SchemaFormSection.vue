<script setup lang="ts">
import {
  computed,
  toRaw,
} from "vue";

import {
  JsonForms,
} from "@jsonforms/vue";

import {
  vanillaRenderers,
} from "@jsonforms/vue-vanilla";

import {
  editorAjv,
} from "../core/ajv";

import {
  DEFAULT_PROFILE_ID,
  getEditorProfile,
} from "../profiles";

import {
  useEditorContext,
} from "../core/context";

import type {
  EditorDocument,
} from "../contracts";

const editor = useEditorContext();

const activeProfile = computed(() => {
  return getEditorProfile(
    editor.profile.value ?? DEFAULT_PROFILE_ID,
  );
});

const schema = computed(() => activeProfile.value.schema);
const uiSchema = computed(() => activeProfile.value.uiSchema);

/*
 * Object.freeze opts this array out of Vue's reactivity proxying
 * entirely (reactive() skips non-extensible objects) — without it,
 * every renderer registry entry's component reference would get
 * wrapped, which is exactly the "Vue made a component reactive"
 * warning class markRaw() exists to avoid elsewhere (see
 * profiles/*.ts's previewComponent/editorComponent).
 */
const renderers = computed(() => Object.freeze([
  ...activeProfile.value.renderers,
  ...vanillaRenderers,
]));

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
  data: EditorDocument;
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
    :ajv="editorAjv"
    validation-mode="ValidateAndShow"
    @change="handleChange"
  />
</template>
