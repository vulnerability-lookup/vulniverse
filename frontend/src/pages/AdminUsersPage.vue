<script setup lang="ts">
import { onMounted, ref } from "vue";

import { apiRequest } from "@/repositories/apiRequest";
import { RepositoryError } from "@/repositories/RepositoryError";
import { useAuthStore } from "@/stores/auth";

interface AdminUser {
  id: number;
  email: string;
  isAdmin: boolean;
  isActive: boolean;
  createdAt: string;
}

const auth = useAuthStore();

const users = ref<AdminUser[]>([]);
const loading = ref(true);
const loadError = ref<string | null>(null);
const pendingUserId = ref<number | null>(null);
const actionError = ref<string | null>(null);

async function loadUsers(): Promise<void> {
  loading.value = true;
  loadError.value = null;

  try {
    users.value = (await apiRequest<{ users: AdminUser[] }>("/admin/users")).users;
  } catch (error) {
    loadError.value = error instanceof Error
      ? error.message
      : "Unable to load users.";
  } finally {
    loading.value = false;
  }
}

async function updateUser(
  user: AdminUser,
  changes: Partial<Pick<AdminUser, "isAdmin" | "isActive">>,
): Promise<void> {
  pendingUserId.value = user.id;
  actionError.value = null;

  try {
    const updated = await apiRequest<AdminUser>(`/admin/users/${user.id}`, {
      method: "PUT",
      body: JSON.stringify(changes),
    });

    Object.assign(user, updated);
  } catch (error) {
    actionError.value = error instanceof RepositoryError
      ? error.message
      : "Unable to update this user.";
  } finally {
    pendingUserId.value = null;
  }
}

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

onMounted(loadUsers);
</script>

<template>
  <main class="container py-5">
    <h1 class="h3 mb-4">Users</h1>

    <div v-if="loading" class="text-secondary">Loading…</div>

    <div v-else-if="loadError" class="alert alert-danger" role="alert">
      {{ loadError }}
      <button
        type="button"
        class="btn btn-outline-danger btn-sm ms-2"
        @click="loadUsers"
      >
        Retry
      </button>
    </div>

    <div v-else>
      <div v-if="actionError" class="alert alert-danger" role="alert">
        {{ actionError }}
      </div>

      <table class="table align-middle">
        <thead>
          <tr>
            <th>Email</th>
            <th>Created</th>
            <th>Status</th>
            <th>Role</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              {{ user.email }}
              <span
                v-if="user.id === auth.currentUser?.id"
                class="badge text-bg-secondary ms-1"
              >
                You
              </span>
            </td>
            <td>{{ formatDate(user.createdAt) }}</td>
            <td>
              <span
                class="badge"
                :class="user.isActive ? 'text-bg-success' : 'text-bg-secondary'"
              >
                {{ user.isActive ? "Active" : "Deactivated" }}
              </span>
            </td>
            <td>
              <span
                class="badge"
                :class="user.isAdmin ? 'text-bg-primary' : 'text-bg-secondary'"
              >
                {{ user.isAdmin ? "Admin" : "User" }}
              </span>
            </td>
            <td class="text-end">
              <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                :disabled="pendingUserId === user.id || user.id === auth.currentUser?.id"
                @click="updateUser(user, { isAdmin: !user.isAdmin })"
              >
                {{ user.isAdmin ? "Revoke admin" : "Make admin" }}
              </button>

              <button
                type="button"
                class="btn btn-outline-secondary btn-sm ms-2"
                :disabled="pendingUserId === user.id || user.id === auth.currentUser?.id"
                @click="updateUser(user, { isActive: !user.isActive })"
              >
                {{ user.isActive ? "Deactivate" : "Reactivate" }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
