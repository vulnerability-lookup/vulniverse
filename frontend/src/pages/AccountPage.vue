<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

/*
 * The logged-in user's own account: changing the password, and deleting
 * the account (backend: api/auth.py, services/accounts.py). Both ask for
 * the current password.
 */

const auth = useAuthStore();
const router = useRouter();

const current = ref("");
const next = ref("");
const repeat = ref("");
const changing = ref(false);
const changeError = ref<string | null>(null);
const changed = ref(false);

const mismatch = computed(() => repeat.value.length > 0 && next.value !== repeat.value);

async function changePassword(): Promise<void> {
  changing.value = true;
  changeError.value = null;
  changed.value = false;

  try {
    await auth.changePassword(current.value, next.value);
    current.value = next.value = repeat.value = "";
    changed.value = true;
  } catch (failure) {
    changeError.value = failure instanceof Error ? failure.message : "Unable to change the password.";
  } finally {
    changing.value = false;
  }
}

const deletePassword = ref("");
const deleting = ref(false);
const deleteError = ref<string | null>(null);

async function deleteAccount(): Promise<void> {
  if (!window.confirm(
    "Delete your account? Your templates and CNA credentials are deleted;"
    + " records you created stay with their organisations. This can't be undone.",
  )) {
    return;
  }

  deleting.value = true;
  deleteError.value = null;

  try {
    await auth.deleteAccount(deletePassword.value);
    await router.replace("/login");
  } catch (failure) {
    deleteError.value = failure instanceof Error ? failure.message : "Unable to delete the account.";
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <main
    class="container py-5"
    style="max-width: 560px;"
  >
    <h1 class="h3 mb-1">
      Account
    </h1>
    <p class="text-secondary mb-4">
      {{ auth.currentUser?.email }}
    </p>

    <form
      class="card card-body mb-4"
      @submit.prevent="changePassword"
    >
      <h2 class="h5">
        Change password
      </h2>

      <div class="mb-3">
        <label
          for="current-password"
          class="form-label"
        >Current password</label>
        <input
          id="current-password"
          v-model="current"
          type="password"
          class="form-control"
          autocomplete="current-password"
          required
        >
      </div>

      <div class="mb-3">
        <label
          for="new-password"
          class="form-label"
        >New password</label>
        <input
          id="new-password"
          v-model="next"
          type="password"
          class="form-control"
          autocomplete="new-password"
          minlength="8"
          required
        >
        <div class="form-text">
          At least 8 characters.
        </div>
      </div>

      <div class="mb-3">
        <label
          for="repeat-password"
          class="form-label"
        >New password again</label>
        <input
          id="repeat-password"
          v-model="repeat"
          type="password"
          class="form-control"
          :class="{ 'is-invalid': mismatch }"
          autocomplete="new-password"
          required
        >
        <div class="invalid-feedback">
          The two don't match.
        </div>
      </div>

      <div
        v-if="changeError"
        class="alert alert-danger"
        role="alert"
      >
        {{ changeError }}
      </div>
      <div
        v-if="changed"
        class="alert alert-success"
        role="status"
      >
        Password changed.
      </div>

      <div>
        <button
          type="submit"
          class="btn btn-primary"
          :disabled="changing || mismatch || !repeat"
        >
          Change password
        </button>
      </div>
    </form>

    <form
      class="card card-body border-danger-subtle"
      @submit.prevent="deleteAccount"
    >
      <h2 class="h5">
        Delete account
      </h2>
      <p class="text-secondary small">
        Your templates and CNA credentials are deleted, and you leave your
        organisations. The records you created stay with them. If you're
        the last admin of an organisation with other members, make one of
        them an admin first.
      </p>

      <div class="mb-3">
        <label
          for="delete-password"
          class="form-label"
        >Your password</label>
        <input
          id="delete-password"
          v-model="deletePassword"
          type="password"
          class="form-control"
          autocomplete="current-password"
          required
        >
      </div>

      <div
        v-if="deleteError"
        class="alert alert-danger"
        role="alert"
      >
        {{ deleteError }}
      </div>

      <div>
        <button
          type="submit"
          class="btn btn-outline-danger"
          :disabled="deleting || !deletePassword"
        >
          Delete my account
        </button>
      </div>
    </form>
  </main>
</template>
