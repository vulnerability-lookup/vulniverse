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

/** Runs a change, shows its error, and keeps the page usable either way. */
async function attempt(action: () => Promise<void>): Promise<void> {
  busy.value = true;
  error.value = null;
  notice.value = null;

  try {
    await action();
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "That didn't work.";
  } finally {
    busy.value = false;
  }
}

const notice = ref<string | null>(null);
const moveTargetId = ref<number | null>(null);

// Other organisations the selected one's records can move to.
const moveTargets = computed(
  () => organisations.value.filter((organisation) => organisation.id !== selectedId.value),
);

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function moveRecords(organisation: Organisation): Promise<void> {
  const target = organisations.value.find((candidate) => candidate.id === moveTargetId.value);

  if (!target || !window.confirm(
    `Move all ${plural(organisation.recordCount, "record")} of ${organisation.name}`
    + ` to ${target.name}? Its members then see them there, and ${organisation.name}'s`
    + " members lose access to them.",
  )) {
    return Promise.resolve();
  }

  return attempt(async () => {
    const result = await apiRequest<{ moved: number }>(
      `/admin/organisations/${organisation.id}/move-records`,
      { method: "POST", body: JSON.stringify({ targetOrganisationId: target.id }) },
    );
    moveTargetId.value = null;
    await loadOrganisations();
    notice.value = `Moved ${plural(result.moved, "record")} to ${target.name}.`;
  });
}

// Members keep their accounts. With records, only unpublished drafts can
// go along (the backend refuses otherwise), after typing the name.
function deleteOrganisation(organisation: Organisation): Promise<void> {
  const count = organisation.memberCount;
  const members = count === 0
    ? "It has no members"
    : `${count === 1 ? "Its member loses" : `Its ${count} members lose`} access (their accounts stay)`;
  let body: object | undefined;

  if (organisation.recordCount === 0) {
    if (!window.confirm(
      `Delete ${organisation.name}? ${members}, and its open invitation links`
      + " stop working. This can't be undone.",
    )) {
      return Promise.resolve();
    }
  } else {
    const typed = window.prompt(
      `Delete ${organisation.name} AND its ${plural(organisation.recordCount, "record")}?`
      + ` ${members}. This can't be undone; only drafts never sent to CVE or`
      + " Vulnerability-Lookup can be deleted this way.\n\n"
      + `Type ${organisation.name} to confirm:`,
    );
    if (typed === null) return Promise.resolve();
    body = { force: true, confirmName: typed.trim() };
  }

  return attempt(async () => {
    await apiRequest(`/admin/organisations/${organisation.id}`, {
      method: "DELETE",
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    await loadOrganisations();
    selectedId.value = organisations.value[0]?.id ?? null;
    notice.value = `Deleted ${organisation.name}.`;
    // You may have been a member, or had it as your current one.
    await auth.fetchMe();
  });
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
      v-if="notice"
      class="alert alert-success"
      role="status"
    >
      {{ notice }}
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

          <form
            v-if="selected.recordCount > 0"
            class="card mt-5"
            @submit.prevent="moveRecords(selected)"
          >
            <div class="card-body">
              <h2 class="h6 mb-1">
                Move records
              </h2>
              <p class="text-secondary small">
                Move all {{ plural(selected.recordCount, "record") }} to another
                organisation, e.g. to merge the two or before deleting this one.
                Nothing moves if the other one already has one of their IDs.
              </p>
              <div class="d-flex flex-wrap gap-2">
                <label
                  for="move-target"
                  class="visually-hidden"
                >Move to</label>
                <select
                  id="move-target"
                  v-model="moveTargetId"
                  class="form-select w-auto flex-grow-1"
                  :disabled="moveTargets.length === 0"
                >
                  <option :value="null">
                    {{ moveTargets.length ? "Move to…" : "No other organisation" }}
                  </option>
                  <option
                    v-for="organisation in moveTargets"
                    :key="organisation.id"
                    :value="organisation.id"
                  >
                    {{ organisation.name }}
                  </option>
                </select>
                <button
                  type="submit"
                  class="btn btn-outline-primary"
                  :disabled="busy || moveTargetId === null"
                >
                  Move {{ plural(selected.recordCount, "record") }}
                </button>
              </div>
            </div>
          </form>

          <div class="card border-danger-subtle mt-3">
            <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-3">
              <div>
                <h2 class="h6 mb-1">
                  Delete organisation
                </h2>
                <p class="text-secondary small mb-0">
                  <template v-if="selected.recordCount">
                    Its {{ plural(selected.recordCount, "record") }} would be deleted too,
                    which works only for drafts never sent to CVE or Vulnerability-Lookup.
                    Move published ones first.
                  </template>
                  <template v-else>
                    Its members lose access; their accounts stay.
                  </template>
                </p>
              </div>
              <button
                type="button"
                class="btn btn-outline-danger text-nowrap"
                :disabled="busy"
                @click="deleteOrganisation(selected)"
              >
                {{ selected.recordCount ? "Delete with its records" : "Delete organisation" }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </main>
</template>
