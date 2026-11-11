<script setup lang="ts">
import {
  computed,
  ref,
  watch,
} from "vue";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  ControlWrapper,
  useVanillaControl,
} from "@jsonforms/vue-vanilla";

import {
  undeclaredEntries,
  withUndeclaredEntries,
} from "./free-form";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * Objects whose schema declares no fields (OSV's database_specific /
 * ecosystem_specific, for example) would otherwise render as an empty
 * group with nothing to edit. Edit them as raw JSON instead: only a
 * valid JSON object (or an empty box, which unsets the field) is
 * written back, so a half-typed value never reaches the record.
 *
 * The layout option json edits a structured object as a whole the same
 * way. With the layout option freeForm, an object that does declare some
 * keys (database_specific.x_gcve, edited by the GCVE editor) uses this
 * too: the box then shows and edits only the other keys and keeps the
 * declared ones as they are.
 */
const jsonForms =
  useJsonFormsControl(props);

const {
  control,
  styles,
  isFocused,
  appliedOptions,
  controlWrapper,
} = useVanillaControl(jsonForms);

// With the layout option json, the whole object is edited as JSON (CSAF's
// recursive product tree, which a generated form can't render).
// So does a composite object (allOf/oneOf/anyOf), which has no form of its
// own (see isCompositeObjectControl).
const declared = computed(() => {
  const schema = control.value.schema;

  return appliedOptions.value.json || schema.allOf || schema.oneOf || schema.anyOf
    ? []
    : Object.keys(schema.properties ?? {});
});

function format(
  value: unknown,
): string {
  const shown = undeclaredEntries(value, declared.value);

  return shown === undefined
    ? ""
    : JSON.stringify(shown, null, 2);
}

function write(
  edited: Record<string, unknown> | undefined,
): void {
  jsonForms.handleChange(
    control.value.path,
    withUndeclaredEntries(control.value.data, declared.value, edited),
  );
}

const text =
  ref(format(control.value.data));

const parseError =
  ref<string | null>(null);

// Follow outside changes (Advanced JSON, reload) but never reformat
// what the user is typing.
watch(
  () => control.value.data,
  (data) => {
    if (!isFocused.value) {
      text.value = format(data);
      parseError.value = null;
    }
  },
);

function onInput(
  event: Event,
): void {
  text.value = (event.target as HTMLTextAreaElement).value;

  if (text.value.trim() === "") {
    parseError.value = null;
    write(undefined);
    return;
  }

  let parsed: unknown;

  try {
    parsed = JSON.parse(text.value);
  } catch (error) {
    parseError.value = (error as Error).message;
    return;
  }

  if (
    typeof parsed !== "object"
    || parsed === null
    || Array.isArray(parsed)
  ) {
    parseError.value = "Must be a JSON object, e.g. {\"key\": \"value\"}.";
    return;
  }

  const editedElsewhere = Object.keys(parsed).find(
    (key) => declared.value.includes(key),
  );

  if (editedElsewhere) {
    parseError.value = `"${editedElsewhere}" has its own section; edit it there.`;
    return;
  }

  parseError.value = null;
  write(parsed as Record<string, unknown>);
}

function onBlur(): void {
  isFocused.value = false;

  if (parseError.value === null) {
    text.value = format(control.value.data);
  }
}
</script>

<template>
  <!-- PascalCase on purpose; see BooleanSelectRenderer.vue. -->
  <ControlWrapper
    v-bind="controlWrapper"
    :styles="styles"
    :is-focused="isFocused"
    :applied-options="appliedOptions"
  >
    <!-- Keeps the error below the box; .wrapper lays children out in a row. -->
    <div class="w-100">
      <textarea
        :id="control.id + '-input'"
        :class="[styles.control.textarea, 'font-monospace', { 'is-invalid': parseError }]"
        :value="text"
        :disabled="!control.enabled"
        placeholder='{ "key": "value" }'
        :aria-invalid="parseError !== null"
        :aria-describedby="parseError ? control.id + '-json-error' : undefined"
        rows="4"
        spellcheck="false"
        @input="onInput"
        @focus="isFocused = true"
        @blur="onBlur"
      />

      <div
        v-if="parseError"
        :id="control.id + '-json-error'"
        class="invalid-feedback d-block"
      >
        Not saved: {{ parseError }}
      </div>
    </div>
  </ControlWrapper>
</template>
