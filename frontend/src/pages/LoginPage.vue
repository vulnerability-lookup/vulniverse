<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";

import { ApiError } from "@/shared/errors";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const email = ref("");
const password = ref("");
const submitting = ref(false);
const error = ref<string | null>(null);
// After a right password, with two-factor authentication set up.
const askCode = ref(false);
const code = ref("");

async function onSubmit(): Promise<void> {
  submitting.value = true;
  error.value = null;

  try {
    if (askCode.value) {
      await auth.loginCode(code.value);
    } else if (await auth.login(email.value, password.value) === "code") {
      askCode.value = true;
      return;
    }

    const redirect = typeof route.query.redirect === "string"
      ? route.query.redirect
      : "/records";

    await router.replace(redirect);
  } catch (err) {
    // 401 at the code step: it took too long; the password again.
    if (askCode.value && err instanceof ApiError && err.status === 401) {
      askCode.value = false;
      code.value = "";
    }
    error.value = err instanceof Error
      ? err.message
      : "Unable to log in.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="container py-5" style="max-width: 480px;">
    <h1 class="h3 mb-4">Log in</h1>

    <form @submit.prevent="onSubmit">
      <div
        v-if="askCode"
        class="mb-3"
      >
        <label
          for="login-code"
          class="form-label"
        >Code from your authenticator app</label>
        <!-- autofocus: the field appears after the password step. -->
        <input
          id="login-code"
          v-model="code"
          class="form-control"
          inputmode="numeric"
          autocomplete="one-time-code"
          pattern="[0-9 ]{6,7}"
          required
          autofocus
        >
      </div>

      <template v-else>
      <div class="mb-3">
        <label for="login-email" class="form-label">Email</label>
        <input
          id="login-email"
          v-model="email"
          type="email"
          class="form-control"
          required
          autocomplete="email"
        >
      </div>

      <div class="mb-3">
        <label for="login-password" class="form-label">Password</label>
        <input
          id="login-password"
          v-model="password"
          type="password"
          class="form-control"
          required
          autocomplete="current-password"
        >
      </div>
      </template>

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
        Log in
      </button>
    </form>

    <p class="mt-3 text-secondary">
      No account yet?
      <RouterLink to="/register">Register</RouterLink>
    </p>
  </main>
</template>
