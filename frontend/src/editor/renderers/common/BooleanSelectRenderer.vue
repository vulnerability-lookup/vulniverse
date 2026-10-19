<script setup lang="ts">
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
 * Vanilla's own BooleanControlRenderer uses a checkbox styled with
 * the same full-width/padded class as every text input — the result
 * is a small checkbox glyph floating in the middle of a stretched
 * box, not a deliberate layout. A True/False/Not set select reads
 * more clearly at a glance and matches every enum field elsewhere
 * in this form, at the cost of one extra click versus toggling a
 * checkbox directly. adaptTarget mirrors vanilla's own
 * EnumControlRenderer convention: the blank option writes back
 * undefined rather than a stringified "" or a guessed default.
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
  (target: HTMLSelectElement) => (target.value === "" ? undefined : target.value === "true"),
);
</script>

<template>
  <!--
    ControlWrapper must stay PascalCase here, not <control-wrapper>:
    in this component's custom-element build, a kebab-case tag with
    no matching global registration resolves as a native custom
    element instead of the imported component and silently renders
    nothing — confirmed by direct A/B rebuild, not a stylistic choice.
  -->
  <ControlWrapper
    v-bind="controlWrapper"
    :styles="styles"
    :is-focused="isFocused"
    :applied-options="appliedOptions"
  >
    <select
      :id="control.id + '-input'"
      :class="styles.control.select"
      :value="control.data === undefined ? '' : String(control.data)"
      :disabled="!control.enabled"
      :autofocus="appliedOptions.focus"
      @change="onChange"
      @focus="isFocused = true"
      @blur="isFocused = false"
    >
      <option value="">
        Not set
      </option>

      <option value="true">
        True
      </option>

      <option value="false">
        False
      </option>
    </select>
  </ControlWrapper>
</template>
