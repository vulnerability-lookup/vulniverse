<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import OrganisationManager from "@/components/OrganisationManager.vue";
import { apiRequest } from "@/repositories/apiRequest";
import { useAuthStore } from "@/stores/auth";

/*
 * Instance admins: every organisation, creating new ones, and managing
 * any of them (OrganisationManager, with adding existing accounts).
 */

interface Organisation {
  id: number;
  name: string;
  slug: string;
  createdAt: string;
  memberCount: number;
  recordCount: number;
}

const auth = useAuthStore();

const organisations = ref<Organisation[]>([]);
const selectedId = ref<number | null>(null);
const loading = ref(true);
const busy = ref(false);
const error = ref<string | null>(null);
const newName = ref("");

const selected = computed(
  () => organisations.value.find((organisation) => organisation.id === selectedId.value) ?? null,
);

async function loadOrganisations(): Promise<void> {
  organisations.value = (
    await apiRequest<{ organisations: Organisation[] }>("/admin/organisations")
  ).organisations;
}

async function createOrganisation(): Promise<void> {
  busy.value = true;
  error.value = null;

  try {
    const created = await apiRequest<Organisation>("/admin/organisations", {
      method: "POST",
      body: JSON.stringify({ name: newName.value }),
    });
    newName.value = "";
    await loadOrganisations();
    selectedId.value = created.id;
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "That didn't work.";
  } finally {
    busy.value = false;
  }
}

// Only an empty organisation can go; its members keep their accounts.
async function deleteOrganisation(organisation: Organisation): Promise<void> {
  const count = organisation.memberCount;
  const members = count === 0
    ? "It has no members"
    : `${count === 1 ? "Its member loses" : `Its ${count} members lose`} access (their accounts stay)`;
  if (!window.confirm(
    `Delete ${organisation.name}? ${members}, and its open invitation links`
    + " stop working. This can't be undone.",
  )) {
    return;
  }

  busy.value = true;
  error.value = null;

  try {
    await apiRequest(`/admin/organisations/${organisation.id}`, { method: "DELETE" });
    await loadOrganisations();
    selectedId.value = organisations.value[0]?.id ?? null;
    // You may have been a member, or had it as your current one.
    await auth.fetchMe();
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "That didn't work.";
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  try {
    await loadOrganisations();
    selectedId.value = organisations.value[0]?.id ?? null;
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "Unable to load organisations.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <main class="container py-5">
    <h1 class="h3 mb-1">
      Organisations
    </h1>
    <p class="text-secondary mb-4">
      Members of an organisation share its records, drafts included.
      Its admins can manage it themselves, under Members in the top bar.
    </p>

    <div
      v-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}
    </div>

    <div
      v-if="loading"
      class="text-secondary"
    >
      Loading…
    </div>

    <div
      v-else
      class="row g-4"
    >
      <div class="col-lg-4">
        <div
          class="list-group mb-3"
          aria-label="Organisations"
        >
          <button
            v-for="organisation in organisations"
            :key="organisation.id"
            type="button"
            class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
            :class="{ active: organisation.id === selectedId }"
            :aria-current="organisation.id === selectedId ? 'true' : undefined"
            @click="selectedId = organisation.id"
          >
            <span>
              {{ organisation.name }}
              <span class="d-block small opacity-75">{{ organisation.slug }}</span>
            </span>
            <span
              class="badge rounded-pill text-bg-secondary"
              :title="`${organisation.memberCount} member(s)`"
            >{{ organisation.memberCount }}</span>
          </button>
        </div>

        <form
          class="card card-body"
          @submit.prevent="createOrganisation"
        >
          <label
            for="new-organisation"
            class="form-label fw-semibold"
          >New organisation</label>
          <div class="input-group">
            <input
              id="new-organisation"
              v-model="newName"
              class="form-control"
              placeholder="e.g. Acme CNA"
              maxlength="128"
              required
            >
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="busy || !newName.trim()"
            >
              Create
            </button>
          </div>
        </form>
      </div>

      <div class="col-lg-8">
        <p
          v-if="!selected"
          class="text-secondary"
        >
          Create an organisation to add members to it.
        </p>

        <!-- :key: a fresh manager per organisation, with its own data. -->
        <template v-else>
          <OrganisationManager
            :key="selected.id"
            :organisation-id="selected.id"
            can-add-accounts
            @changed="loadOrganisations"
          />

          <div class="card border-danger-subtle mt-5">
            <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-3">
              <div>
                <h2 class="h6 mb-1">
                  Delete organisation
                </h2>
                <p class="text-secondary small mb-0">
                  <template v-if="selected.recordCount">
                    {{ selected.name }} still has {{ selected.recordCount }}
                    record{{ selected.recordCount === 1 ? "" : "s" }}; move or delete
                    {{ selected.recordCount === 1 ? "it" : "them" }} first.
                  </template>
                  <template v-else>
                    Its members lose access; their accounts stay.
                  </template>
                </p>
              </div>
              <button
                type="button"
                class="btn btn-outline-danger"
                :disabled="busy || selected.recordCount > 0"
                @click="deleteOrganisation(selected)"
              >
                Delete organisation
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </main>
</template>
