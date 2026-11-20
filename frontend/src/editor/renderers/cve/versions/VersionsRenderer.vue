<script setup lang="ts">
import { computed } from "vue";

import {
  composePaths,
} from "@jsonforms/core";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import { useChangeClass } from "../../../core/changes";
import ChangeBadge from "../../common/ChangeBadge.vue";
import ChangedField from "../../common/ChangedField.vue";
import RemovedItems from "../../common/RemovedItems.vue";
import SuggestField from "../../common/SuggestField.vue";
import { useCollapsibleItems } from "../../common/use-collapsible-items";

import {
  isRange,
  summary,
  upperBoundKey,
  withFields,
  withKind,
  withUpperBound,
} from "./versions";

import type {
  UpperBound,
  VersionEntry,
} from "./versions";

/*
 * An affected product's versions: each a single version or a range,
 * with the range-only fields (upper bound, version type, status
 * changes) shown only for a range. Version types are suggested from the
 * schema's examples (SuggestField). Logic in versions.ts.
 */

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const { control, addItem, removeItems } = useJsonFormsArrayControl(props);
// handleChange sets any nested path (useJsonFormsArrayControl can't).
const { handleChange } = useJsonFormsControl(props);

const items = computed(() => (control.value.data ?? []) as VersionEntry[]);

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
  computed(() => control.value.path),
);

interface ItemSchema {
  properties?: {
    status?: { enum?: string[] };
    versionType?: { examples?: string[] };
  };
}

// From the schema, so a newer CVE schema brings its own values.
const itemSchema = computed(() => control.value.schema as ItemSchema);
const statuses = computed(() => itemSchema.value.properties?.status?.enum ?? ["affected", "unaffected", "unknown"]);
const versionTypes = computed(() => itemSchema.value.properties?.versionType?.examples ?? []);

const changeClass = useChangeClass();

function itemPath(index: number): string {
  return composePaths(control.value.path, `${index}`);
}

function inputId(index: number, field: string): string {
  return `${control.value.id}-${index}-${field}`;
}

function set(index: number, entry: VersionEntry): void {
  handleChange(itemPath(index), entry);
}

function setField(index: number, field: keyof VersionEntry, value: string): void {
  set(index, withFields(items.value[index]!, { [field]: value }));
}

function setBound(index: number, value: string): void {
  const entry = items.value[index]!;
  set(index, { ...entry, [upperBoundKey(entry)]: value });
}

function setChange(index: number, changeIndex: number, field: "at" | "status", value: string): void {
  const changes = [...(items.value[index]!.changes ?? [])];
  changes[changeIndex] = { ...changes[changeIndex], [field]: value };
  set(index, { ...items.value[index]!, changes });
}

function addChange(index: number): void {
  const entry = items.value[index]!;
  set(index, { ...entry, changes: [...(entry.changes ?? []), { at: "", status: "unaffected" }] });
}

function removeChange(index: number, changeIndex: number): void {
  const entry = items.value[index]!;
  const changes = (entry.changes ?? []).filter((_, other) => other !== changeIndex);
  set(index, withFields({ ...entry, changes: changes.length ? changes : undefined }, {}));
}

function addVersion(): void {
  addItem(control.value.path, { version: "", status: "affected" })?.();
}

function removeVersion(index: number): void {
  removeItems?.(control.value.path, [index])?.();
}

// A filled-in entry without these is invalid; an untouched one isn't nagged yet.
function missing(entry: VersionEntry, field: "version" | "versionType" | "bound"): boolean {
  const started = Boolean(entry.version || entry.versionType || entry[upperBoundKey(entry)]);
  if (!started) return false;
  if (field === "version") return !entry.version;
  if (!isRange(entry)) return false;

  return field === "bound" ? !entry[upperBoundKey(entry)] : !entry.versionType;
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h6">
      {{ control.label || "Versions" }}

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="!control.enabled"
        @click="addVersion"
      >
        + Add version
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary small"
    >
      No versions. Without them, the product's default status applies to every version.
    </p>

    <div
      v-for="(entry, index) in items"
      :key="`${control.path}-${index}`"
      :data-path="itemPath(index)"
      class="card mb-2"
      :class="changeClass(itemPath(index))"
    >
      <div class="card-header d-flex justify-content-between align-items-center py-2">
        <span class="fw-semibold small text-truncate">{{ summary(entry) }}</span>

        <div class="d-flex gap-1">
          <ChangeBadge
            :path="itemPath(index)"
            :expanded="isExpanded(index)"
          />

          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            :aria-label="isExpanded(index) ? 'Collapse' : 'Expand'"
            @click="toggle(index)"
          >
            {{ isExpanded(index) ? "▾" : "▸" }}
          </button>

          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            :disabled="!control.enabled"
            @click="removeVersion(index)"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <div
          class="btn-group btn-group-sm mb-3"
          role="group"
          aria-label="Single version or range"
        >
          <button
            type="button"
            class="btn"
            :class="isRange(entry) ? 'btn-outline-secondary' : 'btn-secondary'"
            :aria-pressed="!isRange(entry)"
            :disabled="!control.enabled"
            @click="set(index, withKind(entry, false))"
          >
            Single version
          </button>
          <button
            type="button"
            class="btn"
            :class="isRange(entry) ? 'btn-secondary' : 'btn-outline-secondary'"
            :aria-pressed="isRange(entry)"
            :disabled="!control.enabled"
            @click="set(index, withKind(entry, true))"
          >
            Range
          </button>
        </div>

        <div class="row g-3 align-items-start">
          <ChangedField
            class="col-md-3"
            :path="`${itemPath(index)}.version`"
          >
            <label
              class="form-label"
              :for="inputId(index, 'version')"
            >{{ isRange(entry) ? "From version" : "Version" }}</label>
            <input
              :id="inputId(index, 'version')"
              class="form-control"
              :class="{ 'is-invalid': missing(entry, 'version') }"
              :value="entry.version ?? ''"
              :placeholder="isRange(entry) ? 'e.g. 2.0, or 0 for all earlier' : 'e.g. 2.4.1'"
              :disabled="!control.enabled"
              @input="setField(index, 'version', ($event.target as HTMLInputElement).value)"
            >
            <div class="invalid-feedback">
              Required.
            </div>
          </ChangedField>

          <ChangedField
            v-if="isRange(entry)"
            class="col-md-4"
            :path="`${itemPath(index)}.${upperBoundKey(entry)}`"
          >
            <label
              class="form-label"
              :for="inputId(index, 'bound')"
            >Up to</label>
            <div
              class="input-group"
              :class="{ 'has-validation': missing(entry, 'bound') }"
            >
              <select
                class="form-select flex-grow-0 w-auto"
                aria-label="Below (<) or up to and including (≤)"
                title="< below, ≤ up to and including"
                :value="upperBoundKey(entry)"
                :disabled="!control.enabled"
                @change="set(index, withUpperBound(entry, ($event.target as HTMLSelectElement).value as UpperBound))"
              >
                <option
                  value="lessThan"
                  title="below: this version is not in the range"
                >
                  &lt;
                </option>
                <option
                  value="lessThanOrEqual"
                  title="up to and including: this version is in the range"
                >
                  ≤
                </option>
              </select>
              <input
                :id="inputId(index, 'bound')"
                class="form-control"
                :class="{ 'is-invalid': missing(entry, 'bound') }"
                :value="entry[upperBoundKey(entry)] ?? ''"
                placeholder="e.g. 2.4.1"
                :disabled="!control.enabled"
                @input="setBound(index, ($event.target as HTMLInputElement).value)"
              >
              <div class="invalid-feedback">
                Enter the version the range ends at.
              </div>
            </div>
          </ChangedField>

          <ChangedField
            class="col-md-3"
            :path="`${itemPath(index)}.versionType`"
          >
            <label
              class="form-label"
              :for="inputId(index, 'versionType')"
            >
              Version type
              <span
                v-if="!isRange(entry)"
                class="text-secondary small"
              >(optional)</span>
            </label>
            <SuggestField
              :id="inputId(index, 'versionType')"
              :model-value="entry.versionType ?? ''"
              :options="versionTypes"
              :input-class="['form-control', { 'is-invalid': missing(entry, 'versionType') }]"
              placeholder="e.g. semver"
              :disabled="!control.enabled"
              @update:model-value="(value) => setField(index, 'versionType', value)"
            />
            <div
              v-if="missing(entry, 'versionType')"
              class="invalid-feedback d-block"
            >
              Required for a range: it says how versions compare.
            </div>
            <div
              v-if="entry.versionType === 'custom'"
              class="form-text"
            >
              "custom" means unspecified; use the real numbering if you can.
            </div>
          </ChangedField>

          <ChangedField
            class="col-md-2"
            :path="`${itemPath(index)}.status`"
          >
            <label
              class="form-label"
              :for="inputId(index, 'status')"
            >Status</label>
            <select
              :id="inputId(index, 'status')"
              class="form-select"
              :value="entry.status ?? ''"
              :disabled="!control.enabled"
              @change="setField(index, 'status', ($event.target as HTMLSelectElement).value)"
            >
              <option
                v-for="status in statuses"
                :key="status"
                :value="status"
              >
                {{ status }}
              </option>
            </select>
          </ChangedField>
        </div>

        <template v-if="isRange(entry)">
          <div class="d-flex align-items-center justify-content-between mt-3 mb-1">
            <span class="form-label mb-0">Status changes within the range</span>
            <button
              type="button"
              class="btn btn-outline-primary btn-sm"
              :disabled="!control.enabled"
              @click="addChange(index)"
            >
              + Add status change
            </button>
          </div>
          <p
            v-if="!entry.changes?.length"
            class="small text-secondary mb-0"
          >
            None. E.g. "from 2.3.5: unaffected" for a fix in the middle of the range.
          </p>

          <ChangedField
            v-for="(change, changeIndex) in entry.changes ?? []"
            :key="changeIndex"
            class="row g-2 align-items-center mb-2"
            :path="`${itemPath(index)}.changes.${changeIndex}`"
          >
            <div class="col-auto small">
              From version
            </div>
            <div class="col-md-3">
              <input
                class="form-control form-control-sm"
                :aria-label="`Status change ${changeIndex + 1}: from version`"
                :value="change.at ?? ''"
                placeholder="e.g. 2.3.5"
                :disabled="!control.enabled"
                @input="setChange(index, changeIndex, 'at', ($event.target as HTMLInputElement).value)"
              >
            </div>
            <div class="col-auto small">
              the status is
            </div>
            <div class="col-md-2">
              <select
                class="form-select form-select-sm"
                :aria-label="`Status change ${changeIndex + 1}: status`"
                :value="change.status ?? ''"
                :disabled="!control.enabled"
                @change="setChange(index, changeIndex, 'status', ($event.target as HTMLSelectElement).value)"
              >
                <option
                  v-for="status in statuses"
                  :key="status"
                  :value="status"
                >
                  {{ status }}
                </option>
              </select>
            </div>
            <div class="col-auto">
              <button
                type="button"
                class="btn btn-outline-danger btn-sm"
                :disabled="!control.enabled"
                @click="removeChange(index, changeIndex)"
              >
                Remove
              </button>
            </div>
          </ChangedField>

          <RemovedItems :path="`${itemPath(index)}.changes`" />
        </template>
      </div>
    </div>

    <RemovedItems :path="control.path" />
  </fieldset>
</template>
