<script setup lang="ts">
import type {
  EditorModuleContext,
} from "../contracts";

import CnaPublicationPanel from "./CnaPublicationPanel.vue";

const props = defineProps<{
  context: EditorModuleContext;
}>();
</script>

<template>
  <CnaPublicationPanel
    target="cve-program"
    label="the CVE Program"
    :context="props.context"
  />
</template>
