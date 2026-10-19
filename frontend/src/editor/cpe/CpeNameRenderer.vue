<script setup lang="ts">
import {
  inject,
  ref,
  watch,
} from "vue";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  Resolve,
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
  editorStateKey,
  useEditorRepository,
} from "../core/context";

import {
  useCpeSearch,
} from "./use-cpe-search";

import type {
  CpeSuggestion,
} from "../contracts";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * A plain text control underneath — items of a "CPE Name" array
 * (e.g. affected[].cpes) stay plain pattern-matched strings in the
 * schema, this only adds a live-search suggestion list on top so an
 * unreachable/unsupported CPE Editor (searchCpes is optional on
 * EditorRepository) degrades to normal free-text entry.
 */
const {
  control,
  styles,
  isFocused,
  appliedOptions,
  controlWrapper,
  onChange,
  handleChange,
} = useVanillaControl(
  useJsonFormsControl(props),
  (target: HTMLInputElement) => target.value || undefined,
);

const repository = useEditorRepository();

const editorState = inject(editorStateKey, null);

/*
 * This control only knows its own string value and path (e.g.
 * "containers.cna.affected.0.cpes.0") — vendor/product live on the
 * sibling affected[] entry two path segments up. Reading them this
 * way (inject the live record + Resolve.data) mirrors
 * CpeApplicabilityRenderer.vue's "generate from affected products"
 * lookup, the established pattern for a renderer that needs more
 * than its own control value.
 */
function parentAffectedEntry(): Record<string, unknown> | undefined {
  if (!editorState) {
    return undefined;
  }

  const parentPath = control.value.path
    .split(".")
    .slice(0, -2)
    .join(".");

  const entry = Resolve.data(editorState.record.value, parentPath);

  return entry && typeof entry === "object" ? entry as Record<string, unknown> : undefined;
}

const query = ref(
  typeof control.value.data === "string" ? control.value.data : "",
);

// Resyncs from external changes (e.g. an edit made via the Advanced
// JSON tab) but not while the user is actively typing here.
watch(
  () => control.value.data,
  (value) => {
    if (!isFocused.value) {
      query.value = typeof value === "string" ? value : "";
    }
  },
);

const {
  results,
  loading,
  failed,
  open,
  onQueryChange,
  show,
  hide,
} = useCpeSearch<CpeSuggestion>(
  (term) => {
    const entry = parentAffectedEntry();

    const vendorQ = typeof entry?.vendor === "string" ? entry.vendor : undefined;
    const productQ = typeof entry?.product === "string" ? entry.product : undefined;

    return repository.value?.searchCpes?.({ q: term, vendorQ, productQ }) ?? Promise.resolve([]);
  },
);

function onInput(
  event: Event,
): void {
  query.value = (event.target as HTMLInputElement).value;
  onQueryChange(query.value);
}

function onFocusInput(): void {
  isFocused.value = true;
  show();
}

function onBlurInput(): void {
  isFocused.value = false;
  hide();
}

function select(
  suggestion: CpeSuggestion,
): void {
  query.value = suggestion.cpe;
  hide();
  handleChange(control.value.path, suggestion.cpe);
}
</script>

<template>
  <ControlWrapper
    v-bind="controlWrapper"
    :styles="styles"
    :is-focused="isFocused"
    :applied-options="appliedOptions"
  >
    <div class="reference-id-control">
      <input
        :id="control.id + '-input'"
        :class="styles.control.input"
        :value="query"
        :disabled="!control.enabled"
        :autofocus="appliedOptions.focus"
        :placeholder="appliedOptions.placeholder"
        autocomplete="off"
        @input="onInput"
        @change="onChange"
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
            <span class="fw-semibold">{{ suggestion.cpe }}</span>

            <span
              v-if="suggestion.title"
              class="text-secondary"
            > — {{ suggestion.title }}</span>
          </button>
        </li>
      </ul>

      <div
        v-if="open && loading && !results.length"
        class="text-secondary small mt-1"
      >
        Searching the CPE dictionary…
      </div>

      <div
        v-else-if="open && failed"
        class="text-secondary small mt-1"
      >
        The CPE search timed out or is unavailable — you can still enter
        a CPE string directly.
      </div>
    </div>
  </ControlWrapper>
</template>
