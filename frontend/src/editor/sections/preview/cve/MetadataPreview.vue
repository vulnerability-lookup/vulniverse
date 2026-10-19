<script setup lang="ts">
import type {
  PreviewDate,
} from "./types";


defineProps<{
  primaryIdentifier: string;
  secondaryIdentifier?: string;
  state?: string;
  assigner?: string;
  dates: PreviewDate[];
}>();
</script>


<template>
  <div class="card mb-4">
    <div class="card-body">
      <div
        class="
          d-flex
          flex-wrap
          align-items-center
          gap-2
          mb-2
        "
      >
        <h3 class="h5 mb-0">
          {{ primaryIdentifier }}
        </h3>

        <span
          v-if="secondaryIdentifier"
          class="
            badge
            text-bg-light
            text-secondary
            border
          "
        >
          {{ secondaryIdentifier }}
        </span>

        <span
          v-if="state"
          class="badge text-bg-secondary"
        >
          {{ state }}
        </span>
      </div>

      <dl class="row mb-0 small">
        <template v-if="assigner">
          <dt class="col-sm-3 text-secondary">
            Assigner
          </dt>

          <dd class="col-sm-9">
            {{ assigner }}
          </dd>
        </template>

        <template
          v-for="entry in dates"
          :key="entry.label"
        >
          <dt class="col-sm-3 text-secondary">
            {{ entry.label }}
          </dt>

          <dd class="col-sm-9">
            {{ entry.value }}
          </dd>
        </template>
      </dl>
    </div>
  </div>
</template>
