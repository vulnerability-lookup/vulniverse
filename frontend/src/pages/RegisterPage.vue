<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiRequest } from "@/repositories/apiRequest";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

// From an invitation link's page; the new account joins its organisation.
const invitation = computed(() => (
  typeof route.query.invite === "string" ? route.query.invite : undefined
));

// [server] registration: who may register at all.
const mode = ref<"open" | "invite" | "closed" | null>(null);
const allowed = computed(() => (
  mode.value === "open" || (mode.value === "invite" && invitation.value !== undefined)
));

onMounted(async () => {
  try {
    mode.value = (await apiRequest<{ mode: "open" | "invite" | "closed" }>("/auth/registration")).mode;
  } catch {
    // Let the form show; the backend still decides on submit.
    mode.value = "open";
  }
});

const email = ref("");
const password = ref("");
const submitting = ref(false);
const error = ref<string | null>(null);

async function onSubmit(): Promise<void> {
  submitting.value = true;
  error.value = null;

  try {
    await auth.register(email.value, password.value, invitation.value);
    await router.replace("/records");
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : "Unable to register.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="container py-5" style="max-width: 480px;">
    <h1 class="h3 mb-4">Register</h1>

    <p
      v-if="mode === 'closed'"
      class="alert alert-info"
      role="status"
    >
      Registration is closed on this instance. If you already have an
      account, log in; an invitation link then lets you join its organisation.
    </p>

    <p
      v-else-if="mode === 'invite' && !invitation"
      class="alert alert-info"
      role="status"
    >
      You need an invitation link to register here. Ask an admin of the
      organisation you want to join for one.
    </p>

    <p
      v-if="allowed && invitation"
      class="text-secondary"
    >
      Your account joins the organisation you were invited to.
    </p>

    <form
      v-if="allowed"
      @submit.prevent="onSubmit"
    >
      <div class="mb-3">
        <label for="register-email" class="form-label">Email</label>
        <input
          id="register-email"
          v-model="email"
          type="email"
          class="form-control"
          required
          autocomplete="email"
        >
      </div>

      <div class="mb-3">
        <label for="register-password" class="form-label">Password</label>
        <input
          id="register-password"
          v-model="password"
          type="password"
          class="form-control"
          required
          minlength="8"
          autocomplete="new-password"
        >
        <div class="form-text">At least 8 characters.</div>
      </div>

      <div
        v-if="error"
        class="alert alert-danger"
        role="alert"
      >
        {{ error }}
      </div>

      <button
        type="submit"
        class="btn btn-primary"
        :disabled="submitting"
      >
        Register
      </button>
    </form>

    <p class="mt-3 text-secondary">
      Already have an account?
      <RouterLink :to="invitation ? { name: 'login', query: { redirect: `/invite/${invitation}` } } : '/login'">
        Log in
      </RouterLink>
    </p>
  </main>
</template>
