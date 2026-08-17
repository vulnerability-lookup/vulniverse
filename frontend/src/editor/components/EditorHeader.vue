<script setup lang="ts">
defineProps<{
  identifier: string | null;
  profile: string | null;
  isDraft: boolean;
  dirty: boolean;
  loading: boolean;
}>();

defineEmits<{
  reload: [];
  validate: [];
  save: [];
  publish: [];
  delete: [];
}>();
</script>

<template>
  <header class="editor-header">
    <div
      class="d-flex flex-column flex-lg-row
             align-items-lg-start
             justify-content-between gap-3"
    >
      <div>
        <div
          class="text-primary fw-semibold
                 text-uppercase small mb-1"
        >
          Vulniverse
        </div>

        <h1 class="h3 mb-2">
          {{ identifier ?? "New vulnerability record" }}
        </h1>

        <div
          class="d-flex flex-wrap
                 align-items-center gap-2"
        >
          <span
            v-if="profile"
            class="badge text-bg-secondary"
          >
            {{ profile }}
          </span>

          <span
            v-if="isDraft"
            class="badge text-bg-warning"
          >
            Draft
          </span>

          <span
            v-if="dirty"
            class="badge text-bg-info"
          >
            Unsaved changes
          </span>
        </div>
      </div>

      <div class="d-flex flex-wrap gap-2">
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="loading"
          @click="$emit('reload')"
        >
          Reload
        </button>

        <button
          type="button"
          class="btn btn-outline-primary"
          :disabled="loading"
          @click="$emit('validate')"
        >
          Validate
        </button>

        <button
          type="button"
          class="btn btn-primary"
          :disabled="loading"
          @click="$emit('save')"
        >
          Save
        </button>

        <button
          v-if="isDraft"
          type="button"
          class="btn btn-success"
          :disabled="loading"
          @click="$emit('publish')"
        >
          Publish
        </button>

        <button
          v-if="identifier"
          type="button"
          class="btn btn-outline-danger"
          :disabled="loading"
          @click="$emit('delete')"
        >
          Delete
        </button>
      </div>
    </div>
  </header>
</template>
