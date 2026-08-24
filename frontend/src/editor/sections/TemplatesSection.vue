<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";

import {
  useEditorContext,
} from "../use-editor-context";

import {
  useEditorRepository,
} from "../use-editor-repository";

import {
  applyTemplateFields,
  parseFieldValue,
  stringifyFieldValue,
} from "./apply-template";

import type {
  Template,
  TemplateField,
} from "../contracts";

const editor = useEditorContext();
const repository = useEditorRepository();

const supported = computed(() => !!repository.value?.listTemplates);

const templates = ref<Template[]>([]);
const loadState = ref<"idle" | "loading" | "loaded" | "error">("idle");
const actionError = ref<string | null>(null);
const statusMessage = ref<string | null>(null);

async function loadTemplates(): Promise<void> {
  if (!repository.value?.listTemplates) {
    return;
  }

  loadState.value = "loading";
  actionError.value = null;

  try {
    templates.value = await repository.value.listTemplates();
    loadState.value = "loaded";
  } catch (error) {
    loadState.value = "error";
    actionError.value = error instanceof Error
      ? error.message
      : "Failed to load templates.";
  }
}

onMounted(loadTemplates);

interface DraftField {
  path: string;
  value: string;
}

function emptyDraftField(): DraftField {
  return { path: "", value: "" };
}

const draftName = ref("");
const draftFields = ref<DraftField[]>([emptyDraftField()]);
const saving = ref(false);

// null while creating a new template; the template's id while
// editing an existing one — the same form/fields double as both.
const editingTemplateId = ref<string | null>(null);

function addDraftField(): void {
  draftFields.value.push(emptyDraftField());
}

function removeDraftField(
  index: number,
): void {
  draftFields.value.splice(index, 1);
}

const canSave = computed(() => {
  return draftName.value.trim().length > 0
    && draftFields.value.some((field) => field.path.trim().length > 0);
});

function resetDraft(): void {
  editingTemplateId.value = null;
  draftName.value = "";
  draftFields.value = [emptyDraftField()];
}

function startEdit(
  template: Template,
): void {
  editingTemplateId.value = template.id;
  draftName.value = template.name;
  draftFields.value = template.fields.length
    ? template.fields.map((field) => ({
      path: field.path,
      value: stringifyFieldValue(field.value),
    }))
    : [emptyDraftField()];

  statusMessage.value = null;
  actionError.value = null;
}

async function submitDraft(): Promise<void> {
  if (!canSave.value) {
    return;
  }

  const name = draftName.value.trim();
  const fields: TemplateField[] = draftFields.value
    .filter((field) => field.path.trim().length > 0)
    .map((field) => ({
      path: field.path.trim(),
      value: parseFieldValue(field.value),
    }));

  saving.value = true;
  actionError.value = null;

  try {
    if (editingTemplateId.value) {
      const update = repository.value?.updateTemplate;

      if (!update) {
        return;
      }

      await update(editingTemplateId.value, name, fields);
      statusMessage.value = "Template updated.";
    } else {
      const create = repository.value?.saveTemplate;

      if (!create) {
        return;
      }

      await create(name, fields);
      statusMessage.value = "Template saved.";
    }

    resetDraft();

    await loadTemplates();
  } catch (error) {
    actionError.value = error instanceof Error
      ? error.message
      : "Failed to save the template.";
  } finally {
    saving.value = false;
  }
}

function applyTemplate(
  template: Template,
): void {
  if (!editor.record.value) {
    return;
  }

  applyTemplateFields(
    editor.record.value as unknown as Record<string, unknown>,
    template.fields,
  );

  statusMessage.value = `Applied "${template.name}" to the current record.`;
}

async function deleteTemplate(
  template: Template,
): Promise<void> {
  if (!repository.value?.deleteTemplate) {
    return;
  }

  actionError.value = null;

  try {
    await repository.value.deleteTemplate(template.id);

    if (editingTemplateId.value === template.id) {
      resetDraft();
    }

    await loadTemplates();
  } catch (error) {
    actionError.value = error instanceof Error
      ? error.message
      : "Failed to delete the template.";
  }
}
</script>

<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">
        Templates
      </h2>

      <p class="text-secondary">
        Save a set of field values once, then apply them to fill in
        repeated boilerplate (e.g. vendor/product/CPEs for a tool
        you file many CVEs against) on any record.
      </p>
    </header>

    <p
      v-if="!supported"
      class="text-secondary"
    >
      This host app doesn't support templates.
    </p>

    <template v-else>
      <div
        v-if="statusMessage"
        class="alert alert-success alert-dismissible"
        role="alert"
      >
        {{ statusMessage }}

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="statusMessage = null"
        />
      </div>

      <div
        v-if="actionError"
        class="alert alert-danger alert-dismissible"
        role="alert"
      >
        {{ actionError }}

        <button
          type="button"
          class="btn-close"
          aria-label="Close"
          @click="actionError = null"
        />
      </div>

      <div class="card mb-4">
        <div class="card-header">
          Saved templates
        </div>

        <div class="card-body">
          <p
            v-if="loadState === 'loading'"
            class="text-secondary mb-0"
          >
            Loading…
          </p>

          <p
            v-else-if="!templates.length"
            class="text-secondary mb-0"
          >
            No templates saved yet.
          </p>

          <div v-else>
            <div
              v-for="template in templates"
              :key="template.id"
              class="d-flex justify-content-between align-items-center mb-2"
            >
              <div>
                <span class="fw-semibold">{{ template.name }}</span>

                <span class="text-secondary small ms-2">
                  {{ template.fields.length }} field(s)
                </span>
              </div>

              <div class="d-flex gap-1">
                <button
                  type="button"
                  class="btn btn-outline-primary btn-sm"
                  @click="applyTemplate(template)"
                >
                  Apply
                </button>

                <button
                  type="button"
                  class="btn btn-outline-secondary btn-sm"
                  @click="startEdit(template)"
                >
                  Edit
                </button>

                <button
                  type="button"
                  class="btn btn-outline-danger btn-sm"
                  @click="deleteTemplate(template)"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          {{ editingTemplateId ? "Edit template" : "Create a new template" }}
        </div>

        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Name</label>

            <input
              v-model="draftName"
              type="text"
              class="form-control"
              placeholder="e.g. Acme Widget"
            >
          </div>

          <div
            v-for="(field, index) in draftFields"
            :key="index"
            class="row g-2 mb-2 align-items-end"
          >
            <div class="col-5">
              <label class="form-label">Field path</label>

              <input
                v-model="field.path"
                type="text"
                class="form-control"
                placeholder="containers.cna.affected.0.vendor"
              >
            </div>

            <div class="col-5">
              <label class="form-label">Value</label>

              <input
                v-model="field.value"
                type="text"
                class="form-control"
                placeholder="Acme"
              >
            </div>

            <div class="col-2">
              <button
                type="button"
                class="btn btn-outline-danger btn-sm"
                :disabled="draftFields.length === 1"
                @click="removeDraftField(index)"
              >
                Remove
              </button>
            </div>
          </div>

          <button
            type="button"
            class="btn btn-outline-primary btn-sm mb-3"
            @click="addDraftField"
          >
            + Add field
          </button>

          <div class="d-flex gap-2">
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!canSave || saving"
              @click="submitDraft"
            >
              <template v-if="saving">
                Saving…
              </template>
              <template v-else-if="editingTemplateId">
                Update template
              </template>
              <template v-else>
                Save template
              </template>
            </button>

            <button
              v-if="editingTemplateId"
              type="button"
              class="btn btn-outline-secondary"
              :disabled="saving"
              @click="resetDraft"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
