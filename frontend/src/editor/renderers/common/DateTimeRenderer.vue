<script setup lang="ts">
import {
  computed,
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
  fromPickerValue,
  toPickerValue,
} from "./date-time";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * Replaces vanilla's DateTimeControlRenderer, which showed only
 * minutes and wrote back ":00.000Z", so editing a date silently
 * dropped its seconds. Values are UTC (OSV requires the Z), so the
 * label says so instead of letting people type local time.
 */
const {
  control,
  styles,
  isFocused,
  appliedOptions,
  controlWrapper,
  onChange,
} = useVanillaControl(
  useJsonFormsControl(props),
  (target: HTMLInputElement) => fromPickerValue(target.value),
);

const wrapper = computed(() => ({
  ...controlWrapper.value,
  label: controlWrapper.value.label ? `${controlWrapper.value.label} (UTC)` : "UTC",
}));
</script>

<template>
  <!-- PascalCase on purpose; see BooleanSelectRenderer.vue. -->
  <ControlWrapper
    v-bind="wrapper"
    :styles="styles"
    :is-focused="isFocused"
    :applied-options="appliedOptions"
  >
    <input
      :id="control.id + '-input'"
      type="datetime-local"
      step="1"
      :class="styles.control.input"
      :value="toPickerValue(control.data)"
      :disabled="!control.enabled"
      :autofocus="appliedOptions.focus"
      @change="onChange"
      @focus="isFocused = true"
      @blur="isFocused = false"
    >
  </ControlWrapper>
</template>
