<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  describeMedia,
} from "./supporting-media";

import type {
  SupportingMediaItem,
} from "./supporting-media";

const props = defineProps<{
  media: SupportingMediaItem;
}>();

const described = computed(() => describeMedia(props.media));
</script>

<template>
  <div class="supporting-media-item border rounded p-2 mt-2">
    <div class="text-uppercase text-secondary small mb-1">
      Supporting media
    </div>

    <div
      v-if="described.kind === 'html'"
      class="supporting-media-html"
      v-html="described.html"
    />

    <img
      v-else-if="described.kind === 'image'"
      :src="described.src"
      :alt="`Supporting media (${described.type})`"
      class="img-fluid rounded border"
    >

    <audio
      v-else-if="described.kind === 'audio'"
      :src="described.src"
      controls
      class="w-100"
    />

    <p
      v-else-if="described.kind === 'text'"
      class="mb-0"
    >
      {{ described.text }}
    </p>

    <p
      v-else
      class="text-secondary small mb-0"
    >
      <em>{{ described.reason }}</em>
    </p>
  </div>
</template>
