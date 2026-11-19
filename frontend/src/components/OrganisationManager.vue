<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { apiRequest } from "@/repositories/apiRequest";
import { useAuthStore } from "@/stores/auth";

/*
 * One organisation's name, members and invitation links (backend:
 * api/organisations.py). Used by its own admins (OrganisationPage) and
 * by instance admins (AdminOrganisationsPage), who may also add any
 * existing account directly (`canAddAccounts`); organisation admins
 * invite with a link instead and never see the instance's accounts.
 */

const props = defineProps<{
  organisationId: number;
  canAddAccounts?: boolean;
}>();

const emit = defineEmits<{
  // Name or member count changed: lists showing them should reload.
  changed: [];
}>();

type Role = "admin" | "editor";

interface Organisation {
  id: number;
  name: string;
}

interface Member {
  userId: number;
  email: string;
  isActive: boolean;
  role: Role;
}

interface Invitation {
  id: number;
  role: Role;
  state: "valid" | "accepted" | "revoked" | "expired";
  createdAt: string;
  expiresAt: string;
  createdBy: string | null;
  acceptedBy: string | null;
  // Only right after creating it: the link isn't stored.
  token?: string;
}

interface Account {
  id: number;
  email: string;
  isActive: boolean;
}

const ROLES: { id: Role; label: string }[] = [
  { id: "editor", label: "Editor" },
  { id: "admin", label: "Admin" },
];

const STATE_LABELS: Record<Invitation["state"], string> = {
  valid: "Open",
  accepted: "Used",
  revoked: "Revoked",
  expired: "Expired",
};

const auth = useAuthStore();

const name = ref("");
const savedName = ref("");
const members = ref<Member[]>([]);
const invitations = ref<Invitation[]>([]);
const accounts = ref<Account[]>([]);

const busy = ref(false);
const error = ref<string | null>(null);
const inviteRole = ref<Role>("editor");
const newLink = ref<string | null>(null);
const copied = ref(false);
const addAccountId = ref<number | null>(null);
const addRole = ref<Role>("editor");

const base = computed(() => `/organisations/${props.organisationId}`);

const addableAccounts = computed(() => {
  const inside = new Set(members.value.map((member) => member.userId));

  return accounts.value.filter((account) => account.isActive && !inside.has(account.id));
});

function linkFor(token: string): string {
  return new URL(`${import.meta.env.BASE_URL}invite/${token}`, window.location.origin).href;
}

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

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

async function load(): Promise<void> {
  const [memberList, invitationList] = await Promise.all([
    apiRequest<{ members: Member[] }>(`${base.value}/members`),
    apiRequest<{ invitations: Invitation[] }>(`${base.value}/invitations`),
  ]);

  members.value = memberList.members;
  invitations.value = invitationList.invitations;
}

// The current user's own role or organisation names may have changed.
async function afterChange(userId?: number): Promise<void> {
  await load();
  emit("changed");
  if (userId === undefined || userId === auth.currentUser?.id) await auth.fetchMe();
}

function rename(): Promise<void> {
  return attempt(async () => {
    const updated = await apiRequest<Organisation>(base.value, {
      method: "PATCH",
      body: JSON.stringify({ name: name.value }),
    });
    savedName.value = updated.name;
    await afterChange();
  });
}

function setRole(userId: number, role: Role): Promise<void> {
  return attempt(async () => {
    try {
      await apiRequest(`${base.value}/members/${userId}`, {
        method: "PUT",
        body: JSON.stringify({ role }),
      });
    } catch (failure) {
      // Refused (e.g. the last admin): the dropdown would show the
      // refused role until the next reload.
      await load();
      throw failure;
    }
    await afterChange(userId);
  });
}

function removeMember(member: Member): Promise<void> {
  if (!window.confirm(`Remove ${member.email}? The records they created stay with the organisation.`)) {
    return Promise.resolve();
  }

  return attempt(async () => {
    await apiRequest(`${base.value}/members/${member.userId}`, { method: "DELETE" });
    await afterChange(member.userId);
  });
}

function addAccount(): Promise<void> {
  const userId = addAccountId.value;
  addAccountId.value = null;

  return userId === null ? Promise.resolve() : setRole(userId, addRole.value);
}

function createInvitation(): Promise<void> {
  return attempt(async () => {
    const created = await apiRequest<Invitation>(`${base.value}/invitations`, {
      method: "POST",
      body: JSON.stringify({ role: inviteRole.value }),
    });
    newLink.value = created.token ? linkFor(created.token) : null;
    copied.value = false;
    await load();
  });
}

async function copyLink(): Promise<void> {
  if (!newLink.value) return;

  try {
    await navigator.clipboard.writeText(newLink.value);
    copied.value = true;
  } catch {
    // No clipboard access (e.g. plain http): the link stays selectable.
    error.value = "Couldn't copy automatically; select the link and copy it.";
  }
}

function revoke(invitation: Invitation): Promise<void> {
  return attempt(async () => {
    await apiRequest(`${base.value}/invitations/${invitation.id}`, { method: "DELETE" });
    await load();
  });
}

onMounted(() => attempt(async () => {
  const [organisation] = await Promise.all([
    apiRequest<Organisation>(base.value),
    load(),
  ]);
  savedName.value = organisation.name;
  name.value = organisation.name;

  if (props.canAddAccounts) {
    accounts.value = (await apiRequest<{ users: Account[] }>("/admin/users")).users;
  }
}));
</script>

<template>
  <div>
    <div
      v-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}
    </div>

    <form
      class="d-flex gap-2 mb-4"
      @submit.prevent="rename"
    >
      <label
        for="organisation-name"
        class="visually-hidden"
      >Name</label>
      <input
        id="organisation-name"
        v-model="name"
        class="form-control"
        maxlength="128"
        required
      >
      <button
        type="submit"
        class="btn btn-outline-primary text-nowrap"
        :disabled="busy || !name.trim() || name.trim() === savedName"
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
      v-if="canAddAccounts"
      class="d-flex flex-wrap gap-2 mb-4"
      @submit.prevent="addAccount"
    >
      <label
        for="add-account"
        class="visually-hidden"
      >Existing account</label>
      <select
        id="add-account"
        v-model="addAccountId"
        class="form-select w-auto flex-grow-1"
        :disabled="addableAccounts.length === 0"
      >
        <option :value="null">
          {{ addableAccounts.length ? "Add an existing account…" : "Every active account is a member" }}
        </option>
        <option
          v-for="account in addableAccounts"
          :key="account.id"
          :value="account.id"
        >
          {{ account.email }}
        </option>
      </select>
      <label
        for="add-account-role"
        class="visually-hidden"
      >Role</label>
      <select
        id="add-account-role"
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
        :disabled="busy || addAccountId === null"
      >
        Add
      </button>
    </form>

    <h2 class="h5 mt-4">
      Invitation links
    </h2>
    <p class="text-secondary small">
      Anyone with a link can join once, with its role, within seven days;
      it's shown only now, so send it right away.
    </p>

    <form
      class="d-flex flex-wrap gap-2 mb-3"
      @submit.prevent="createInvitation"
    >
      <label
        for="invite-role"
        class="visually-hidden"
      >Role for the new member</label>
      <select
        id="invite-role"
        v-model="inviteRole"
        class="form-select w-auto"
      >
        <option
          v-for="role in ROLES"
          :key="role.id"
          :value="role.id"
        >
          Join as {{ role.label.toLowerCase() }}
        </option>
      </select>
      <button
        type="submit"
        class="btn btn-outline-primary"
        :disabled="busy"
      >
        Create link
      </button>
    </form>

    <div
      v-if="newLink"
      class="alert alert-success"
      role="status"
    >
      <label
        for="new-invitation-link"
        class="form-label fw-semibold"
      >New invitation link</label>
      <div class="input-group">
        <input
          id="new-invitation-link"
          class="form-control font-monospace"
          :value="newLink"
          readonly
          @focus="($event.target as HTMLInputElement).select()"
        >
        <button
          type="button"
          class="btn btn-outline-secondary"
          @click="copyLink"
        >
          {{ copied ? "Copied" : "Copy" }}
        </button>
      </div>
    </div>

    <table
      v-if="invitations.length"
      class="table table-sm align-middle"
    >
      <thead>
        <tr>
          <th>Role</th>
          <th>Status</th>
          <th>Created</th>
          <th>Expires</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="invitation in invitations"
          :key="invitation.id"
        >
          <td>{{ invitation.role === "admin" ? "Admin" : "Editor" }}</td>
          <td>
            {{ STATE_LABELS[invitation.state] }}
            <span
              v-if="invitation.acceptedBy"
              class="text-secondary"
            >by {{ invitation.acceptedBy }}</span>
          </td>
          <td>{{ formatDate(invitation.createdAt) }}<span v-if="invitation.createdBy" class="text-secondary"> by {{ invitation.createdBy }}</span></td>
          <td>{{ formatDate(invitation.expiresAt) }}</td>
          <td class="text-end">
            <button
              v-if="invitation.state === 'valid'"
              type="button"
              class="btn btn-outline-danger btn-sm"
              :disabled="busy"
              @click="revoke(invitation)"
            >
              Revoke
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
