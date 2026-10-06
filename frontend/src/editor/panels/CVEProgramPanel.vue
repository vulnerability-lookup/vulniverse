<script setup lang="ts">
import type {
  EditorContext,
} from "../contracts";

import CnaPublicationPanel from "./CnaPublicationPanel.vue";

const props = defineProps<{
  context: EditorContext;
}>();
</script>

<template>
  <CnaPublicationPanel
    target="cve-program"
    label="the CVE Program"
    :context="props.context"
  />
</template>
