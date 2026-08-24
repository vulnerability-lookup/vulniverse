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
  useEditorRepository,
} from "../use-editor-repository";

import {
  loadReferenceList,
  referenceKindForPattern,
} from "./reference-lookup";

import type {
  ReferenceListItem,
} from "../contracts";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * A plain text control underneath — cweId/capecId stay pattern-
 * matched strings in the schema, this only adds a filtered
 * suggestion list on top so a stale/unreachable reference list (or
 * an ID published after our last cache refresh) degrades to normal
 * free-text entry rather than blocking anything.
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

const kind = computed(() => {
  const schema = control.value.schema as { pattern?: string } | undefined;

  return referenceKindForPattern(schema?.pattern);
});

const items = ref<ReferenceListItem[]>([]);
const loadState = ref<"idle" | "loading" | "loaded" | "error">("idle");
const showSuggestions = ref(false);

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

function ensureLoaded(): void {
  if (loadState.value !== "idle" || !kind.value || !repository.value) {
    return;
  }

  loadState.value = "loading";

  loadReferenceList(repository.value, kind.value)
    .then((loaded) => {
      items.value = loaded;
      loadState.value = "loaded";
    })
    .catch(() => {
      loadState.value = "error";
    });
}

const filtered = computed(() => {
  const term = query.value.trim().toLowerCase();

  if (!term) {
    return [];
  }

  return items.value
    .filter(
      (item) => item.id.toLowerCase().includes(term)
        || item.name.toLowerCase().includes(term),
    )
    .slice(0, 30);
});

function onInput(
  event: Event,
): void {
  query.value = (event.target as HTMLInputElement).value;
  showSuggestions.value = true;
}

function onFocusInput(): void {
  isFocused.value = true;
  showSuggestions.value = true;
  ensureLoaded();
}

function onBlurInput(): void {
  isFocused.value = false;
  showSuggestions.value = false;
}

function select(
  item: ReferenceListItem,
): void {
  query.value = item.id;
  showSuggestions.value = false;
  handleChange(control.value.path, item.id);
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
        v-if="showSuggestions && filtered.length"
        class="reference-id-suggestions"
      >
        <li
          v-for="item in filtered"
          :key="item.id"
        >
          <button
            type="button"
            class="reference-id-suggestion"
            @mousedown.prevent="select(item)"
          >
            <span class="fw-semibold">{{ item.id }}</span>
            <span class="text-secondary"> — {{ item.name }}</span>
          </button>
        </li>
      </ul>

      <div
        v-if="showSuggestions && loadState === 'loaded' && query.trim() && !filtered.length"
        class="text-secondary small mt-1"
      >
        No match in the local {{ kind?.toUpperCase() }} list — you can still enter this ID directly.
      </div>
    </div>
  </ControlWrapper>
</template>
