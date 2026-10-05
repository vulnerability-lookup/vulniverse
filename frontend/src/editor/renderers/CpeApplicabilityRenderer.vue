<script setup lang="ts">
import {
  computed,
  inject,
  ref,
} from "vue";

import {
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  composePaths,
  resolveData,
} from "@jsonforms/core";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  editorStateKey,
} from "../editor-context";

import {
  useCollapsibleItems,
} from "./use-collapsible-items";

import {
  fromVersionFields,
  generateConditionsFromAffected,
  toVersionFields,
} from "./cpe-applicability";

import type {
  AffectedEntry,
  CpeGroup,
  CpeMatch,
  CpeStatement,
} from "./cpe-applicability";

import CpeConditionDialog from "./CpeConditionDialog.vue";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

const { handleChange } = useJsonFormsControl(props);

/*
 * Whole-record read for "Generate from affected products" — the
 * idiomatic way to reach sibling data from a renderer scoped to its
 * own control's data/path. Optional (default null) since nothing else
 * in this renderer strictly requires an editor host to be present.
 */
const editorState = inject(editorStateKey, null);

/*
 * This renderer is mounted both for containers.cna.cpeApplicability
 * and, per-entry, for containers.adp.<index>.cpeApplicability (see
 * AdpRenderer.vue's FIELD_OPTIONS) — control.value.path already
 * reflects whichever one, e.g. "containers.adp.0.cpeApplicability".
 * Swapping the last path segment for "affected" and resolving it
 * against the whole record (via @jsonforms/core's own resolveData,
 * the same path format control.path already uses) finds the correct
 * sibling affected[] generically, without this component needing to
 * know which container it's nested under.
 */
const affectedEntries = computed(() => {
  const record = editorState?.record.value;

  if (!record) {
    return [];
  }

  const segments = control.value.path.split(".");
  const siblingPath = [...segments.slice(0, -1), "affected"].join(".");

  return (resolveData(record, siblingPath) ?? []) as AffectedEntry[];
});

const statements = computed(() => {
  return (control.value.data ?? []) as CpeStatement[];
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => statements.value.length),
);

function statementPath(
  sIndex: number,
): string {
  return composePaths(
    control.value.path,
    `${sIndex}`,
  );
}

function updateStatement(
  sIndex: number,
  patch: Partial<CpeStatement>,
): void {
  const current = statements.value[sIndex];

  if (!current) {
    return;
  }

  handleChange(
    statementPath(sIndex),
    { ...current, ...patch },
  );
}

function updateGroup(
  sIndex: number,
  nIndex: number,
  patch: Partial<CpeGroup>,
): void {
  const statement = statements.value[sIndex];

  if (!statement) {
    return;
  }

  const nodes = statement.nodes.map(
    (group, index) => (index === nIndex ? { ...group, ...patch } : group),
  );

  updateStatement(sIndex, { nodes });
}

function addStatement(): void {
  addItem(
    control.value.path,
    { operator: "AND", nodes: [] },
  )?.();
}

function removeStatement(
  sIndex: number,
): void {
  removeItems?.(control.value.path, [sIndex])?.();
}

function setStatementOperator(
  sIndex: number,
  operator: "AND" | "OR",
): void {
  updateStatement(sIndex, { operator });
}

function setStatementNegate(
  sIndex: number,
  negate: boolean,
): void {
  updateStatement(sIndex, { negate });
}

function addGroup(
  sIndex: number,
): void {
  const statement = statements.value[sIndex];

  if (!statement) {
    return;
  }

  updateStatement(sIndex, {
    nodes: [...statement.nodes, { operator: "OR", cpeMatch: [] }],
  });
}

function removeGroup(
  sIndex: number,
  nIndex: number,
): void {
  const statement = statements.value[sIndex];

  if (!statement) {
    return;
  }

  updateStatement(sIndex, {
    nodes: statement.nodes.filter((_, index) => index !== nIndex),
  });
}

function setGroupOperator(
  sIndex: number,
  nIndex: number,
  operator: "AND" | "OR",
): void {
  updateGroup(sIndex, nIndex, { operator });
}

function setGroupNegate(
  sIndex: number,
  nIndex: number,
  negate: boolean,
): void {
  updateGroup(sIndex, nIndex, { negate });
}

function removeCondition(
  sIndex: number,
  nIndex: number,
  mIndex: number,
): void {
  const group = statements.value[sIndex]?.nodes[nIndex];

  if (!group) {
    return;
  }

  updateGroup(sIndex, nIndex, {
    cpeMatch: group.cpeMatch.filter((_, index) => index !== mIndex),
  });
}

/*
 * One line of English for a condition's version constraint — purely
 * presentational, so it stays local to this component rather than
 * living in cpe-applicability.ts alongside the data-shape helpers.
 */
function versionSummary(
  match: CpeMatch,
): string {
  const constraint = fromVersionFields(match);

  if (constraint.mode === "any") {
    return "any version";
  }

  if (constraint.mode === "exact") {
    return `version ${constraint.value}`;
  }

  const from = constraint.from
    ? `${constraint.from.inclusive ? ">=" : ">"} ${constraint.from.value}`
    : null;

  const to = constraint.to
    ? `${constraint.to.inclusive ? "<=" : "<"} ${constraint.to.value}`
    : null;

  return [from, to].filter(Boolean).join(" and ") || "any version";
}

const conditionDialogRef = ref<InstanceType<typeof CpeConditionDialog> | null>(null);

const editingContext = ref<{
  sIndex: number;
  nIndex: number;
  mIndex: number | null;
} | null>(null);

function openAddCondition(
  sIndex: number,
  nIndex: number,
): void {
  editingContext.value = { sIndex, nIndex, mIndex: null };
  conditionDialogRef.value?.open();
}

function openEditCondition(
  sIndex: number,
  nIndex: number,
  mIndex: number,
): void {
  const match = statements.value[sIndex]?.nodes[nIndex]?.cpeMatch[mIndex];

  if (!match) {
    return;
  }

  editingContext.value = { sIndex, nIndex, mIndex };
  conditionDialogRef.value?.open(match);
}

function applyCondition(
  match: CpeMatch,
): void {
  const context = editingContext.value;

  if (!context) {
    return;
  }

  const group = statements.value[context.sIndex]?.nodes[context.nIndex];

  if (!group) {
    return;
  }

  const cpeMatch =
    context.mIndex === null
      ? [...group.cpeMatch, match]
      : group.cpeMatch.map((existing, index) => (index === context.mIndex ? match : existing));

  updateGroup(context.sIndex, context.nIndex, { cpeMatch });
  editingContext.value = null;
}

/*
 * Reads containers.cna.affected and bootstraps one "Any of these"
 * group of vulnerable conditions from it — a convenience starting
 * point, not an exact mapping (see cpe-applicability.ts). Always
 * targets the first statement (creating one if none exists yet) since
 * most records have at most one; the user can restructure manually
 * afterward via Add group/Edit/Remove.
 */
const environmentHintVisible = ref(false);
const environmentHintStatementIndex = ref<number | null>(null);

function generateFromAffected(): void {
  const generated = generateConditionsFromAffected(affectedEntries.value);

  if (generated.length === 0) {
    return;
  }

  const cpeMatch: CpeMatch[] = generated.map((condition) => ({
    vulnerable: true,
    criteria: condition.criteria,
    ...toVersionFields(condition.versionConstraint),
  }));

  const newGroup: CpeGroup = { operator: "OR", cpeMatch };

  if (statements.value.length === 0) {
    addItem(
      control.value.path,
      { operator: "AND", nodes: [newGroup] },
    )?.();
  } else {
    updateStatement(0, {
      nodes: [...statements.value[0]!.nodes, newGroup],
    });
  }

  environmentHintStatementIndex.value = 0;
  environmentHintVisible.value = true;
}

function addEnvironmentCondition(): void {
  const sIndex = environmentHintStatementIndex.value;
  const statement = sIndex === null ? undefined : statements.value[sIndex];

  environmentHintVisible.value = false;

  if (sIndex === null || !statement) {
    return;
  }

  const nIndex = statement.nodes.length;

  updateStatement(sIndex, {
    operator: "AND",
    nodes: [...statement.nodes, { operator: "OR", cpeMatch: [] }],
  });

  editingContext.value = { sIndex, nIndex, mIndex: null };
  conditionDialogRef.value?.open({ vulnerable: false, criteria: "" });
}

function statementLabel(
  sIndex: number,
): string {
  const statement = statements.value[sIndex];
  const groupCount = statement?.nodes.length ?? 0;

  return `Statement ${sIndex + 1} (${groupCount} ${groupCount === 1 ? "group" : "groups"})`;
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h5">
      CPE Applicability

      <button
        type="button"
        class="btn btn-primary btn-sm"
        :disabled="!control.enabled"
        @click="addStatement"
      >
        + Add statement
      </button>
    </legend>

    <p
      v-if="statements.length === 0"
      class="text-secondary"
    >
      No applicability rules defined.
    </p>

    <div class="d-flex gap-2 mb-3">
      <button
        v-if="affectedEntries.length"
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="!control.enabled"
        @click="generateFromAffected"
      >
        + Generate from affected products
      </button>
    </div>

    <div
      v-if="environmentHintVisible"
      class="alert alert-info alert-dismissible d-flex justify-content-between align-items-center"
      role="status"
    >
      <span>
        Does applicability also depend on an operating system, hardware
        platform, or another product?
      </span>

      <div class="d-flex align-items-center gap-2">
        <button
          type="button"
          class="btn btn-outline-primary btn-sm text-nowrap"
          @click="addEnvironmentCondition"
        >
          + Add environment condition
        </button>

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="environmentHintVisible = false"
        />
      </div>
    </div>

    <div
      v-for="(statement, sIndex) in statements"
      :key="`${control.path}-${sIndex}`"
      class="card mb-2"
    >
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-semibold">
          {{ statementLabel(sIndex) }}
        </span>

        <div class="d-flex gap-1">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            @click="toggle(sIndex)"
          >
            {{ isExpanded(sIndex) ? "▾" : "▸" }}
          </button>

          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            :disabled="!control.enabled"
            @click="removeStatement(sIndex)"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(sIndex)"
        class="card-body"
      >
        <label class="form-label">Match</label>

        <div class="mb-2">
          <div class="form-check">
            <input
              :id="`cpe-stmt-and-${sIndex}`"
              class="form-check-input"
              type="radio"
              :checked="(statement.operator ?? 'AND') === 'AND'"
              :disabled="!control.enabled"
              @change="setStatementOperator(sIndex, 'AND')"
            >

            <label
              class="form-check-label"
              :for="`cpe-stmt-and-${sIndex}`"
            >
              ALL of the following groups
            </label>
          </div>

          <div class="form-check">
            <input
              :id="`cpe-stmt-or-${sIndex}`"
              class="form-check-input"
              type="radio"
              :checked="statement.operator === 'OR'"
              :disabled="!control.enabled"
              @change="setStatementOperator(sIndex, 'OR')"
            >

            <label
              class="form-check-label"
              :for="`cpe-stmt-or-${sIndex}`"
            >
              ANY of the following groups
            </label>
          </div>
        </div>

        <div class="form-check mb-3">
          <input
            :id="`cpe-stmt-negate-${sIndex}`"
            class="form-check-input"
            type="checkbox"
            :checked="Boolean(statement.negate)"
            :disabled="!control.enabled"
            @change="setStatementNegate(sIndex, ($event.target as HTMLInputElement).checked)"
          >

          <label
            class="form-check-label"
            :for="`cpe-stmt-negate-${sIndex}`"
          >
            Negate whole rule
          </label>
        </div>

        <div
          v-for="(group, nIndex) in statement.nodes"
          :key="`${control.path}-${sIndex}-${nIndex}`"
          class="border rounded p-2 mb-2"
        >
          <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="d-flex align-items-center gap-2">
              <select
                class="form-select form-select-sm"
                style="width: auto"
                :value="group.operator"
                :disabled="!control.enabled"
                @change="setGroupOperator(sIndex, nIndex, ($event.target as HTMLSelectElement).value as 'AND' | 'OR')"
              >
                <option value="OR">Any of these</option>
                <option value="AND">All of these</option>
              </select>

              <div class="form-check mb-0">
                <input
                  :id="`cpe-group-negate-${sIndex}-${nIndex}`"
                  class="form-check-input"
                  type="checkbox"
                  :checked="Boolean(group.negate)"
                  :disabled="!control.enabled"
                  @change="setGroupNegate(sIndex, nIndex, ($event.target as HTMLInputElement).checked)"
                >

                <label
                  class="form-check-label"
                  :for="`cpe-group-negate-${sIndex}-${nIndex}`"
                >
                  Negate this group
                </label>
              </div>
            </div>

            <button
              type="button"
              class="btn btn-outline-danger btn-sm"
              :disabled="!control.enabled"
              @click="removeGroup(sIndex, nIndex)"
            >
              Remove group
            </button>
          </div>

          <p
            v-if="group.cpeMatch.length === 0"
            class="text-secondary small mb-2"
          >
            No conditions yet.
          </p>

          <ul
            v-else
            class="list-unstyled mb-2"
          >
            <li
              v-for="(match, mIndex) in group.cpeMatch"
              :key="`${control.path}-${sIndex}-${nIndex}-${mIndex}`"
              class="d-flex justify-content-between align-items-start border-bottom py-1 gap-2"
            >
              <div>
                <span
                  class="badge me-2"
                  :class="match.vulnerable === false ? 'text-bg-secondary' : 'text-bg-danger'"
                >
                  {{ match.vulnerable === false ? "Required environment" : "Vulnerable" }}
                </span>

                <code>{{ match.criteria }}</code>

                <div class="text-secondary small">
                  {{ versionSummary(match) }}
                </div>
              </div>

              <div class="d-flex gap-1 text-nowrap">
                <button
                  type="button"
                  class="btn btn-outline-secondary btn-sm"
                  :disabled="!control.enabled"
                  @click="openEditCondition(sIndex, nIndex, mIndex)"
                >
                  Edit
                </button>

                <button
                  type="button"
                  class="btn btn-outline-danger btn-sm"
                  :disabled="!control.enabled"
                  @click="removeCondition(sIndex, nIndex, mIndex)"
                >
                  Remove
                </button>
              </div>
            </li>
          </ul>

          <button
            type="button"
            class="btn btn-outline-primary btn-sm"
            :disabled="!control.enabled"
            @click="openAddCondition(sIndex, nIndex)"
          >
            + Add condition
          </button>
        </div>

        <button
          type="button"
          class="btn btn-outline-primary btn-sm"
          :disabled="!control.enabled"
          @click="addGroup(sIndex)"
        >
          + Add group
        </button>
      </div>
    </div>

    <CpeConditionDialog
      ref="conditionDialogRef"
      @apply="applyCondition"
    />
  </fieldset>
</template>
