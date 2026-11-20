<script setup lang="ts">
import { computed, ref } from "vue";
import type { ClassValue } from "vue";

import { matchingOptions } from "./suggestions";

/*
 * A text field with a fixed list of suggestions that opens on the first
 * click or focus (the browser's <datalist> needs a second click), is
 * filtered while typing, and works with the arrow keys, Enter and Esc.
 * Any other text can still be typed. For a list to search on a server,
 * see cpe/CpeAutocompleteField.vue.
 */

const props = defineProps<{
  modelValue: string;
  options: readonly string[];
  id: string;
  inputClass?: ClassValue;
  disabled?: boolean;
  placeholder?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const open = ref(false);
const active = ref(-1);
// Filtered only once something is typed: a click shows every option,
// even when the field holds a value that isn't one of them.
const typing = ref(false);
const listId = computed(() => `${props.id}-suggestions`);
const shown = computed(() => (typing.value ? matchingOptions(props.options, props.modelValue) : [...props.options]));

function show(): void {
  if (props.disabled) return;
  if (!open.value) typing.value = false;
  open.value = true;
  active.value = -1;
}

function close(): void {
  open.value = false;
  active.value = -1;
}

function onInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
  show();
  typing.value = true;
}

function choose(option: string): void {
  emit("update:modelValue", option);
  close();
}

function onKeydown(event: KeyboardEvent): void {
  const count = shown.value.length;

  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    if (!open.value) show();
    if (!count) return;
    const step = event.key === "ArrowDown" ? 1 : -1;
    active.value = (active.value + step + count) % count;
  } else if (event.key === "Enter" && open.value && active.value >= 0) {
    event.preventDefault();
    choose(shown.value[active.value]!);
  } else if (event.key === "Escape" && open.value) {
    // Only the list closes, not a dialog or menu around the field.
    event.stopPropagation();
    close();
  }
}
</script>

<template>
  <div class="reference-id-control">
    <input
      :id="id"
      :value="modelValue"
      :class="inputClass"
      :disabled="disabled"
      :placeholder="placeholder"
      autocomplete="off"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="open && shown.length > 0"
      :aria-controls="listId"
      :aria-activedescendant="active >= 0 ? `${listId}-${active}` : undefined"
      @input="onInput"
      @focus="show"
      @click="show"
      @blur="close"
      @keydown="onKeydown"
    >

    <ul
      v-show="open && shown.length"
      :id="listId"
      role="listbox"
      class="reference-id-suggestions"
    >
      <li
        v-for="(option, index) in shown"
        :id="`${listId}-${index}`"
        :key="option"
        role="option"
        :aria-selected="index === active"
        class="reference-id-suggestion"
        :class="{ active: index === active }"
        @mousedown.prevent="choose(option)"
      >
        {{ option }}
      </li>
    </ul>
  </div>
</template>
