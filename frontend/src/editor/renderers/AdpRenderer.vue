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
  createDefaultValue,
} from "@jsonforms/core";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  useCollapsibleItems,
} from "./use-collapsible-items";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

/*
 * Same reasoning as ArrayCardRenderer's optional-at-floor handling:
 * containers.adp is optional (only "cna" is required on
 * containers) but has schema.minItems set, so removing the last
 * entry must clear the whole property rather than leave an
 * invalid too-short array.
 */
const { handleChange } = useJsonFormsControl(props);

const items = computed(() => {
  return (control.value.data ?? []) as Array<
    Record<string, any>
  >;
});

const atMinItems = computed(() => {
  const minItems = control.value.arraySchema?.minItems ?? 0;

  return items.value.length <= minItems;
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

/*
 * An ADP container has ~19 properties — essentially a second CNA
 * container. Mounting all of them at once is exactly what crashed
 * "affected" (13 properties) before that got its own flat
 * dispatch, except ADP is bigger and several of its own fields
 * (affected, metrics, references, credits, timeline,
 * cpeApplicability) are themselves full sub-trees — confirmed by
 * testing that the aggregate is too large to mount simultaneously
 * no matter how each individual field is dispatched. CNA's own
 * equivalent fields are spread across 8 top-level app tabs so no
 * single click ever mounts all of them together; this replicates
 * that same decomposition one level deeper, inside each ADP card,
 * so only the active section's fields are ever mounted.
 */
interface Section {
  id: string;
  label: string;
  fields: string[];
}

const SECTIONS: Section[] = [
  {
    id: "metadata",
    label: "Metadata",
    fields: ["providerMetadata", "title", "datePublic"],
  },
  {
    id: "descriptions",
    label: "Descriptions",
    fields: ["descriptions"],
  },
  {
    id: "affected",
    label: "Affected",
    fields: ["affected"],
  },
  {
    id: "classification",
    label: "Classification",
    fields: ["problemTypes", "impacts"],
  },
  {
    id: "severity",
    label: "Severity",
    fields: ["metrics", "cpeApplicability"],
  },
  {
    id: "guidance",
    label: "Guidance",
    fields: ["configurations", "workarounds", "solutions", "exploits"],
  },
  {
    id: "references",
    label: "References",
    fields: ["references"],
  },
  {
    id: "credits",
    label: "Credits",
    fields: ["credits", "timeline", "source", "tags", "taxonomyMappings"],
  },
];

const DEFAULT_SECTION_ID = SECTIONS[0]!.id;

const activeSections = ref<Record<number, string>>({});

function activeSectionOf(
  index: number,
): string {
  return activeSections.value[index] ?? DEFAULT_SECTION_ID;
}

function selectSection(
  index: number,
  sectionId: string,
): void {
  activeSections.value[index] = sectionId;
}

function fieldsFor(
  index: number,
): string[] {
  const section = SECTIONS.find(
    (candidate) => candidate.id === activeSectionOf(index),
  );

  return section?.fields ?? [];
}

/*
 * containers.cna's equivalent affected/metrics/references/source/
 * tags fields get their named renderer through cve.layout.json's
 * controlOptions, keyed by the cna-specific path. ADP entries have
 * the same fields but no matching controlOptions entry, so without
 * this map they'd fall through to the generic ArrayCardRenderer —
 * which flattens each metric format object (e.g. cvssV4_0's 21
 * properties) into a plain object Control, reproducing the same
 * Generate.uiSchema crash the named renderers exist to avoid.
 * (tags needs no knownTags override here — TagsRenderer derives
 * its known values straight from the schema, and ADP's own "tags"
 * field (adpTags) has a different, smaller enum than CNA's anyway.)
 */
const FIELD_OPTIONS: Record<string, Record<string, unknown>> = {
  affected: { renderer: "vulniverse-affected" },
  metrics: { renderer: "vulniverse-metrics" },
  references: { renderer: "vulniverse-references" },
  source: { renderer: "vulniverse-source" },
  tags: { renderer: "vulniverse-tags" },
};

function controlFor(
  key: string,
): ControlElement {
  const options = FIELD_OPTIONS[key];

  return {
    type: "Control",
    scope: `#/properties/${key}`,
    ...(options ? { options } : {}),
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

function labelFor(
  index: number,
): string {
  const providerMetadata = items.value[index]?.providerMetadata;

  return providerMetadata?.shortName
    || providerMetadata?.orgId
    || `ADP entry ${index + 1}`;
}

function addEntry(): void {
  addItem(
    control.value.path,
    createDefaultValue(
      control.value.schema,
      control.value.rootSchema,
    ),
  )?.();
}

function deleteEntry(
  index: number,
): void {
  if (atMinItems.value) {
    if (control.value.required) {
      return;
    }

    handleChange(
      control.value.path,
      undefined,
    );

    return;
  }

  removeItems?.(control.value.path, [index])?.();
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
        @click="addEntry"
      >
        + Add ADP entry
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary"
    >
      No ADP entries yet.
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-3"
    >
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-semibold">
          {{ labelFor(index) }}
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
            :disabled="!control.enabled || (control.required && atMinItems)"
            @click="deleteEntry(index)"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <nav
          class="nav nav-pills mb-3"
          aria-label="ADP entry sections"
        >
          <button
            v-for="section in SECTIONS"
            :key="section.id"
            type="button"
            class="nav-link"
            :class="{ active: activeSectionOf(index) === section.id }"
            @click="selectSection(index, section.id)"
          >
            {{ section.label }}
          </button>
        </nav>

        <div
          v-for="key in fieldsFor(index)"
          :key="key"
          class="mb-3"
        >
          <dispatch-renderer
            :schema="control.schema"
            :uischema="controlFor(key)"
            :path="itemPath(index)"
            :enabled="control.enabled"
            :renderers="control.renderers"
            :cells="control.cells"
          />
        </div>
      </div>
    </div>
  </fieldset>
</template>
