<script setup lang="ts">
import {
  RouterView,
} from "vue-router";

import AppHeader from "@/components/AppHeader.vue";
const isGithubPages =
  import.meta.env.MODE === "github-pages";
</script>

<template>
  <AppHeader v-if="!isGithubPages" />
  <!-- A new record page starts over when its query (a Patch2Vuln
       candidate) changes; other pages keep their instance. -->
  <RouterView v-slot="{ Component, route }">
    <component
      :is="Component"
      :key="route.name === 'editor-new' ? route.fullPath : route.name"
    />
  </RouterView>
</template>
