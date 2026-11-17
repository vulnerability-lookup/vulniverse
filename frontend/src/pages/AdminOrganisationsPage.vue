<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { apiRequest } from "@/repositories/apiRequest";
import { useAuthStore } from "@/stores/auth";

/*
 * Instance admins manage organisations and their members here (backend:
 * api/organisations.py). Removing someone ends their access to the
 * organisation's drafts; the records they created stay with it.
 */

interface Organisation {
  id: number;
  name: string;
  slug: string;
  createdAt: string;
  memberCount: number;
}

interface Member {
  userId: number;
  email: string;
  isActive: boolean;
  role: Role;
}

interface User {
  id: number;
  email: string;
  isActive: boolean;
}

type Role = "admin" | "editor";

const ROLES: { id: Role; label: string }[] = [
  { id: "editor", label: "Editor" },
  { id: "admin", label: "Admin" },
];

const auth = useAuthStore();

const organisations = ref<Organisation[]>([]);
const users = ref<User[]>([]);
const members = ref<Member[]>([]);
const selectedId = ref<number | null>(null);

const loading = ref(true);
const busy = ref(false);
const error = ref<string | null>(null);

const newName = ref("");
const renameTo = ref("");
const addUserId = ref<number | null>(null);
const addRole = ref<Role>("editor");

const selected = computed(
  () => organisations.value.find((organisation) => organisation.id === selectedId.value) ?? null,
);

// Active accounts not yet in the selected organisation.
const addableUsers = computed(() => {
  const inside = new Set(members.value.map((member) => member.userId));

  return users.value.filter((user) => user.isActive && !inside.has(user.id));
});

/** Runs a change, shows its error, and keeps the page usable either way. */
async function attempt(action: () => Promise<void>): Promise<void> {
  busy.value = true;
  error.value = null;

  try {
    await action();
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "That didn't work.";
  } finally {
    busy.value = false;
  }
}

async function loadOrganisations(): Promise<void> {
  organisations.value = (
    await apiRequest<{ organisations: Organisation[] }>("/admin/organisations")
  ).organisations;
}

async function select(id: number): Promise<void> {
  selectedId.value = id;
  renameTo.value = selected.value?.name ?? "";
  addUserId.value = null;
  members.value = (
    await apiRequest<{ members: Member[] }>(`/admin/organisations/${id}/members`)
  ).members;
}

// The member counts in the list follow member changes.
async function reloadSelected(): Promise<void> {
  await loadOrganisations();
  if (selectedId.value !== null) await select(selectedId.value);
}

function createOrganisation(): Promise<void> {
  return attempt(async () => {
    const created = await apiRequest<Organisation>("/admin/organisations", {
      method: "POST",
      body: JSON.stringify({ name: newName.value }),
    });
    newName.value = "";
    await loadOrganisations();
    await select(created.id);
  });
}

function rename(): Promise<void> {
  return attempt(async () => {
    await apiRequest(`/admin/organisations/${selectedId.value}`, {
      method: "PATCH",
      body: JSON.stringify({ name: renameTo.value }),
    });
    await reloadSelected();
    // Your own switcher shows organisation names too.
    await auth.fetchMe();
  });
}

function setRole(userId: number, role: Role): Promise<void> {
  return attempt(async () => {
    await apiRequest(`/admin/organisations/${selectedId.value}/members/${userId}`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    });
    await reloadSelected();
    if (userId === auth.currentUser?.id) await auth.fetchMe();
  });
}

function addMember(): Promise<void> {
  const userId = addUserId.value;

  return userId === null ? Promise.resolve() : setRole(userId, addRole.value);
}

function removeMember(member: Member): Promise<void> {
  if (!window.confirm(`Remove ${member.email} from ${selected.value?.name}? Their records stay with the organisation.`)) {
    return Promise.resolve();
  }

  return attempt(async () => {
    await apiRequest(`/admin/organisations/${selectedId.value}/members/${member.userId}`, {
      method: "DELETE",
    });
    await reloadSelected();
    if (member.userId === auth.currentUser?.id) await auth.fetchMe();
  });
}

onMounted(() => attempt(async () => {
  try {
    await loadOrganisations();
    users.value = (await apiRequest<{ users: User[] }>("/admin/users")).users;

    const first = organisations.value[0];
    if (first) await select(first.id);
  } finally {
    loading.value = false;
  }
}));
</script>

<template>
  <main class="container py-5">
    <h1 class="h3 mb-1">
      Organisations
    </h1>
    <p class="text-secondary mb-4">
      Members of an organisation share its records, drafts included.
      New records go to the organisation chosen in the top bar.
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
            @click="attempt(() => select(organisation.id))"
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

        <template v-else>
          <form
            class="d-flex gap-2 mb-4"
            @submit.prevent="rename"
          >
            <label
              for="rename-organisation"
              class="visually-hidden"
            >Name</label>
            <input
              id="rename-organisation"
              v-model="renameTo"
              class="form-control"
              maxlength="128"
              required
            >
            <button
              type="submit"
              class="btn btn-outline-primary text-nowrap"
              :disabled="busy || !renameTo.trim() || renameTo.trim() === selected.name"
            >
              Rename
            </button>
          </form>

          <h2 class="h5">
            Members
          </h2>

          <table class="table align-middle">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="member in members"
                :key="member.userId"
              >
                <td>
                  {{ member.email }}
                  <span
                    v-if="member.userId === auth.currentUser?.id"
                    class="badge text-bg-secondary ms-1"
                  >You</span>
                  <span
                    v-if="!member.isActive"
                    class="badge text-bg-secondary ms-1"
                  >Deactivated</span>
                </td>
                <td>
                  <select
                    class="form-select form-select-sm w-auto"
                    :aria-label="`Role of ${member.email}`"
                    :value="member.role"
                    :disabled="busy"
                    @change="setRole(member.userId, ($event.target as HTMLSelectElement).value as Role)"
                  >
                    <option
                      v-for="role in ROLES"
                      :key="role.id"
                      :value="role.id"
                    >
                      {{ role.label }}
                    </option>
                  </select>
                </td>
                <td class="text-end">
                  <button
                    type="button"
                    class="btn btn-outline-danger btn-sm"
                    :disabled="busy"
                    @click="removeMember(member)"
                  >
                    Remove
                  </button>
                </td>
              </tr>
              <tr v-if="members.length === 0">
                <td
                  colspan="3"
                  class="text-secondary"
                >
                  No members yet.
                </td>
              </tr>
            </tbody>
          </table>

          <form
            class="d-flex flex-wrap gap-2"
            @submit.prevent="addMember"
          >
            <label
              for="add-member"
              class="visually-hidden"
            >User</label>
            <select
              id="add-member"
              v-model="addUserId"
              class="form-select w-auto flex-grow-1"
              :disabled="addableUsers.length === 0"
            >
              <option :value="null">
                {{ addableUsers.length ? "Add a user…" : "Every active user is a member" }}
              </option>
              <option
                v-for="user in addableUsers"
                :key="user.id"
                :value="user.id"
              >
                {{ user.email }}
              </option>
            </select>
            <label
              for="add-member-role"
              class="visually-hidden"
            >Role</label>
            <select
              id="add-member-role"
              v-model="addRole"
              class="form-select w-auto"
            >
              <option
                v-for="role in ROLES"
                :key="role.id"
                :value="role.id"
              >
                {{ role.label }}
              </option>
            </select>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="busy || addUserId === null"
            >
              Add
            </button>
          </form>

          <p class="form-text mt-3">
            For now both roles may work on all records; organisation admins
            managing their own members comes later.
          </p>
        </template>
      </div>
    </div>
  </main>
</template>
