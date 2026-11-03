<script setup lang="ts">
import {
  ref,
  watch,
} from "vue";

import {
  useEditorRepository,
} from "../core/context";

import {
  useCpeSearch,
} from "./use-cpe-search";

/*
 * A plain text field underneath — "vendor"/"product" stay free text
 * in the schema, this only adds a live-search suggestion list on top
 * so an unreachable/unsupported CPE Editor (searchCpeVendors/
 * searchCpeProducts are optional on EditorRepository) degrades to
 * normal free-text entry. Shared by the vendor and product fields in
 * AffectedRenderer.vue — both return the same {id, name, title?}
 * suggestion shape; the product field additionally narrows by
 * vendorQuery (see props below).
 */
const props = defineProps<{
  modelValue: string;
  method: "searchCpeVendors" | "searchCpeProducts";
  kind: string;
  id?: string;
  inputClass?: string;
  disabled?: boolean;
  placeholder?: string;
  // Only meaningful when method is "searchCpeProducts" — the sibling
  // vendor field's current text, used to narrow product suggestions
  // to that vendor. Ignored for the vendor field itself.
  vendorQuery?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [
    value: string,
  ];
}>();

interface Suggestion {
  id: string;
  name: string;
  title?: string | null;
}

const repository = useEditorRepository();

const query = ref(props.modelValue);
const isFocused = ref(false);

watch(
  () => props.modelValue,
  (value) => {
    if (!isFocused.value) {
      query.value = value;
    }
  },
);

const {
  results,
  loading,
  failed,
  open,
  onQueryChange,
  hide,
} = useCpeSearch<Suggestion>(
  (term) => {
    if (props.method === "searchCpeProducts") {
      return repository.value?.searchCpeProducts?.(term, props.vendorQuery) ?? Promise.resolve([]);
    }

    return repository.value?.searchCpeVendors?.(term) ?? Promise.resolve([]);
  },
);

function onInput(
  event: Event,
): void {
  query.value = (event.target as HTMLInputElement).value;
  emit("update:modelValue", query.value);
  onQueryChange(query.value);
}

function onFocusInput(): void {
  isFocused.value = true;
}

function onBlurInput(): void {
  isFocused.value = false;
  hide();
}

function select(
  suggestion: Suggestion,
): void {
  query.value = suggestion.name;
  emit("update:modelValue", suggestion.name);
  hide();
}
</script>

<template>
  <div class="reference-id-control">
    <input
      :id="id"
      :value="query"
      :class="inputClass"
      :disabled="disabled"
      :placeholder="placeholder"
      autocomplete="off"
      @input="onInput"
      @focus="onFocusInput"
      @blur="onBlurInput"
    >

    <ul
      v-if="open && results.length"
      class="reference-id-suggestions"
    >
      <li
        v-for="suggestion in results"
        :key="suggestion.id"
      >
        <button
          type="button"
          class="reference-id-suggestion"
          @mousedown.prevent="select(suggestion)"
        >
          <span class="fw-semibold">{{ suggestion.name }}</span>

          <span
            v-if="suggestion.title && suggestion.title !== suggestion.name"
            class="text-secondary"
          > — {{ suggestion.title }}</span>
        </button>
      </li>
    </ul>

    <div
      v-if="open && loading && !results.length"
      class="text-secondary small mt-1"
    >
      Searching CPE {{ kind }}s…
    </div>

    <div
      v-else-if="open && failed"
      class="text-secondary small mt-1"
    >
      The CPE {{ kind }} search timed out or is unavailable — you can
      still enter a {{ kind }} name directly.
    </div>
  </div>
</template>
