<script setup lang="ts">
import vulniverseLogo from "../../assets/vulniverse-logo.png";

defineProps<{
  identifier: string | null;
  profile: string | null;
  isDraft: boolean;
  isRejected: boolean;
  dirty: boolean;
  loading: boolean;
  modules: Array<{
    id: string;
    label: string;
    enabled: boolean;
  }>;
}>();

defineEmits<{
  reload: [];
  validate: [];
  save: [];
  publish: [];
  unpublish: [];
  reject: [];
  delete: [];
  runModule: [
    id: string,
  ];
}>();
</script>

<template>
  <header class="editor-header">
    <div class="editor-header-grid">
      <div class="editor-header-logo-slot">
        <img
          :src="vulniverseLogo"
          alt="Vulniverse"
          class="editor-header-logo"
        >
      </div>

      <div
        class="editor-header-main
               d-flex flex-column flex-lg-row
               align-items-lg-center
               justify-content-between gap-3"
      >
        <div>
          <h1 class="h5 mb-1">
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
              v-if="isRejected"
              class="badge text-bg-danger"
            >
              Rejected
            </span>

            <span
              v-if="dirty"
              class="badge text-bg-info"
            >
              Unsaved changes
            </span>
          </div>
        </div>

      <div class="d-flex flex-wrap align-items-center gap-2">
        <div
          class="btn-group"
          role="group"
          aria-label="Editor actions"
        >
          <button
            type="button"
            class="btn btn-sm btn-outline-secondary"
            :disabled="loading"
            @click="$emit('reload')"
          >
            <svg
              class="editor-header-icon"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            ><path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9" /><path d="M13.5 2.5v3h-3" /></svg>
            Reload
          </button>

          <button
            type="button"
            class="btn btn-sm btn-outline-primary"
            :disabled="loading"
            @click="$emit('validate')"
          >
            <svg
              class="editor-header-icon"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            ><polyline points="3 8 6.5 11.5 13 4.5" /></svg>
            Validate
          </button>
        </div>

        <div
          class="vr d-none d-md-block"
          aria-hidden="true"
        />

        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="loading"
          @click="$emit('save')"
        >
          <svg
            class="editor-header-icon"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          ><path d="M2.5 2.5h8l3 3v8h-11z" /><path d="M5 2.5v3h4v-3M5 13.5v-4h6v4" /></svg>
          Save
        </button>

        <button
          v-if="isDraft"
          type="button"
          class="btn btn-sm btn-success"
          :disabled="loading"
          @click="$emit('publish')"
        >
          Publish
        </button>

        <button
          v-if="!isDraft"
          type="button"
          class="btn btn-sm btn-outline-warning"
          :disabled="loading"
          @click="$emit('unpublish')"
        >
          Revert to draft
        </button>

        <template v-if="modules.length">
          <div
            class="vr d-none d-md-block"
            aria-hidden="true"
          />

          <button
            v-for="module in modules"
            :key="module.id"
            type="button"
            class="btn btn-sm btn-outline-primary"
            :disabled="loading || !module.enabled"
            @click="$emit('runModule', module.id)"
          >
            {{ module.label }}
          </button>
        </template>

        <template v-if="identifier && !isRejected">
          <div
            class="vr d-none d-md-block"
            aria-hidden="true"
          />

          <button
            type="button"
            class="btn btn-sm btn-outline-danger"
            :disabled="loading"
            @click="$emit('reject')"
          >
            <svg
              class="editor-header-icon"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            ><circle cx="8" cy="8" r="6" /><line
              x1="4"
              y1="4"
              x2="12"
              y2="12"
            /></svg>
            Reject
          </button>
        </template>

        <template v-if="identifier">
          <div
            class="vr d-none d-md-block"
            aria-hidden="true"
          />

          <button
            type="button"
            class="btn btn-sm btn-outline-danger"
            :disabled="loading"
            @click="$emit('delete')"
          >
            <svg
              class="editor-header-icon"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            ><path d="M3 4h10M6 4V2.5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1V4M4.5 4l.5 9a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1l.5-9" /></svg>
            Delete
          </button>
        </template>
      </div>
    </div>
    </div>
  </header>
</template>
