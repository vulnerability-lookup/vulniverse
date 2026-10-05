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
  <RouterView />
</template>
