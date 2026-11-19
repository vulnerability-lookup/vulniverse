<script setup lang="ts">
import { computed } from "vue";

import OrganisationManager from "@/components/OrganisationManager.vue";
import { useAuthStore } from "@/stores/auth";

/*
 * The current organisation (the one chosen in the top bar), for its
 * admins: members, roles and invitation links.
 */

const auth = useAuthStore();

const organisation = computed(() => auth.currentOrganisation);
const canManage = computed(
  () => organisation.value?.role === "admin" || Boolean(auth.currentUser?.isAdmin),
);
</script>

<template>
  <main class="container py-5">
    <h1 class="h3 mb-1">
      {{ organisation?.name ?? "Organisation" }}
    </h1>
    <p class="text-secondary mb-4">
      Members share this organisation's records, drafts included.
    </p>

    <p
      v-if="!organisation"
      class="text-secondary"
    >
      You're not a member of any organisation yet.
    </p>

    <p
      v-else-if="!canManage"
      class="text-secondary"
    >
      Only the organisation's admins manage its members.
    </p>

    <!-- :key: switching organisations in the top bar shows the new one. -->
    <OrganisationManager
      v-else
      :key="organisation.id"
      :organisation-id="organisation.id"
    />
  </main>
</template>
