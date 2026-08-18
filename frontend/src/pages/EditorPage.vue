<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  useRoute,
  useRouter,
} from "vue-router";

import VulniverseEditor from
  "@/editor/VulniverseEditor.ce.vue";

import {
  HttpRepository,
} from "@/repositories/HttpRepository";

const route = useRoute();
const router = useRouter();

const repository =
  new HttpRepository("/api/v1");

const recordId = computed(() => {
  const parameter =
    route.params.recordId;

  if (Array.isArray(parameter)) {
    return parameter[0] ?? "";
  }

  return parameter ?? "";
});

function handleLoaded(
  identifier: string,
): void {
  console.info(
    "Opened vulnerability record:",
    identifier,
  );
}

function handleError(
  error: Error,
): void {
  console.error(
    "Editor error:",
    error,
  );
}

function handleDeleted(
  identifier: string,
): void {
  console.info(
    "Deleted vulnerability record:",
    identifier,
  );

  router.push("/");
}
</script>

<template>
  <VulniverseEditor
    :repository="repository"
    mode="edit"
    :record-id="recordId"
    @loaded="handleLoaded"
    @error="handleError"
    @deleted="handleDeleted"
  />
</template>
