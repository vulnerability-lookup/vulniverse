<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  composePaths,
} from "@jsonforms/core";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  useCollapsibleItems,
} from "../common/use-collapsible-items";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

const items = computed(() => {
  return (control.value.data ?? []) as Array<
    Record<string, unknown>
  >;
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

/*
 * useJsonFormsArrayControl only exposes addItem/removeItems/
 * moveUp/moveDown — none of them can set an arbitrary nested path
 * (needed for the tag pills below). useJsonFormsControl, called
 * on the same props, additionally provides handleChange(path,
 * value), which dispatches through the same underlying store.
 */
const { handleChange } = useJsonFormsControl(props);

const KNOWN_TAGS = [
  "broken-link",
  "customer-entitlement",
  "exploit",
  "government-resource",
  "issue-tracking",
  "mailing-list",
  "mitigation",
  "not-applicable",
  "patch",
  "permissions-required",
  "media-coverage",
  "product",
  "related",
  "release-notes",
  "signature",
  "technical-description",
  "third-party-advisory",
  "vendor-advisory",
  "vdb-entry",
];

const customTagInput = ref<Record<number, string>>({});

function controlFor(
  key: string,
): ControlElement {
  return {
    type: "Control",
    scope: `#/properties/${key}`,
  };
}

function itemPath(
  index: number,
): string {
  return composePaths(
    control.value.path,
    `${index}`,
  );
}

function tagsOf(
  index: number,
): string[] {
  const tags = items.value[index]?.tags;

  return Array.isArray(tags)
    ? (tags as string[])
    : [];
}

function setTags(
  index: number,
  tags: string[],
): void {
  handleChange(
    composePaths(
      itemPath(index),
      "tags",
    ),
    tags,
  );
}

function toggleTag(
  index: number,
  tag: string,
): void {
  const current = tagsOf(index);

  setTags(
    index,
    current.includes(tag)
      ? current.filter((value) => value !== tag)
      : [...current, tag],
  );
}

function addCustomTag(
  index: number,
): void {
  const value = customTagInput.value[index]?.trim();

  if (!value) {
    return;
  }

  const tag = value.startsWith("x_")
    ? value
    : `x_${value}`;

  setTags(
    index,
    [...tagsOf(index), tag],
  );

  customTagInput.value[index] = "";
}

function removeTag(
  index: number,
  tag: string,
): void {
  setTags(
    index,
    tagsOf(index).filter((value) => value !== tag),
  );
}

function addReference(): void {
  addItem(
    control.value.path,
    {},
  )?.();
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h5">
      {{ control.label }}

      <button
        type="button"
        class="btn btn-primary btn-sm"
        :disabled="!control.enabled"
        @click="addReference"
      >
        + Add reference
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary"
    >
      No references yet.
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-3"
    >
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-semibold text-truncate">
          {{ (item.url as string | undefined) || `Reference ${index + 1}` }}
        </span>

        <div class="d-flex gap-1">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            @click="toggle(index)"
          >
            {{ isExpanded(index) ? "▾" : "▸" }}
          </button>

          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            :disabled="!control.enabled"
            @click="removeItems?.(control.path, [index])?.()"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <div class="row g-3 mb-3">
          <div class="col-md-8">
            <dispatch-renderer
              :schema="control.schema"
              :uischema="controlFor('url')"
              :path="itemPath(index)"
              :enabled="control.enabled"
              :renderers="control.renderers"
              :cells="control.cells"
            />
          </div>

          <div class="col-md-4">
            <dispatch-renderer
              :schema="control.schema"
              :uischema="controlFor('name')"
              :path="itemPath(index)"
              :enabled="control.enabled"
              :renderers="control.renderers"
              :cells="control.cells"
            />
          </div>
        </div>

        <label class="form-label">Tags</label>

        <div class="d-flex flex-wrap gap-2 mb-2">
          <button
            v-for="tag in KNOWN_TAGS"
            :key="tag"
            type="button"
            class="btn btn-sm"
            :class="
              tagsOf(index).includes(tag)
                ? 'btn-primary'
                : 'btn-outline-secondary'
            "
            :disabled="!control.enabled"
            @click="toggleTag(index, tag)"
          >
            {{ tag }}
          </button>
        </div>

        <div
          v-if="tagsOf(index).some((tag) => tag.startsWith('x_'))"
          class="d-flex flex-wrap gap-2 mb-2"
        >
          <span
            v-for="tag in tagsOf(index).filter((t) => t.startsWith('x_'))"
            :key="tag"
            class="badge text-bg-secondary d-flex align-items-center gap-1"
          >
            {{ tag }}

            <button
              type="button"
              class="btn-close btn-close-white"
              style="font-size: 0.55rem"
              :disabled="!control.enabled"
              @click="removeTag(index, tag)"
            />
          </span>
        </div>

        <div class="d-flex gap-2">
          <input
            v-model="customTagInput[index]"
            type="text"
            class="form-control form-control-sm"
            placeholder="Custom tag (x_...)"
            :disabled="!control.enabled"
            @keydown.enter.prevent="addCustomTag(index)"
          >

          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            :disabled="!control.enabled"
            @click="addCustomTag(index)"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  </fieldset>
</template>
