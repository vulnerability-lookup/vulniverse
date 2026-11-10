<script setup lang="ts">
import {
  nextTick,
  onMounted,
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
 * A one-line value (e.g. a CVE title, up to 256 characters) that
 * wraps and grows instead of scrolling out of sight in an <input>.
 * Turned on per field with controlOptions.<path>.wrap in a layout
 * file. Line breaks are blocked, so the value stays a single line.
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
  // Pasted line breaks become spaces.
  (target: HTMLTextAreaElement) => target.value === ""
    ? undefined
    : target.value.replace(/\s*[\r\n]+\s*/g, " "),
);

const textarea = ref<HTMLTextAreaElement | null>(null);

// Grow to fit the text; field-sizing: content isn't in every browser.
function fit(): void {
  const element = textarea.value;

  if (element) {
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight + 2}px`;
  }
}

onMounted(fit);

watch(
  () => control.value.data,
  () => nextTick(fit),
);
</script>

<template>
  <!-- PascalCase on purpose; see BooleanSelectRenderer.vue. -->
  <ControlWrapper
    v-bind="controlWrapper"
    :styles="styles"
    :is-focused="isFocused"
    :applied-options="appliedOptions"
  >
    <textarea
      :id="control.id + '-input'"
      ref="textarea"
      :class="[styles.control.textarea, 'editor-wrap-text']"
      :value="control.data ?? ''"
      :disabled="!control.enabled"
      :autofocus="appliedOptions.focus"
      :placeholder="appliedOptions.placeholder"
      rows="1"
      @input="onChange($event); fit()"
      @keydown.enter.prevent
      @focus="isFocused = true"
      @blur="isFocused = false"
    />
  </ControlWrapper>
</template>
