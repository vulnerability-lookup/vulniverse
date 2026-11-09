<script setup lang="ts">
import {
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

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * Objects whose schema declares no fields (OSV's database_specific /
 * ecosystem_specific, for example) would otherwise render as an empty
 * group with nothing to edit. Edit them as raw JSON instead: only a
 * valid JSON object (or an empty box, which unsets the field) is
 * written back, so a half-typed value never reaches the record.
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

function format(
  value: unknown,
): string {
  return value === undefined
    ? ""
    : JSON.stringify(value, null, 2);
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
    jsonForms.handleChange(control.value.path, undefined);
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

  parseError.value = null;
  jsonForms.handleChange(control.value.path, parsed);
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
