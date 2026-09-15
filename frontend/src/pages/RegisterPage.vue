<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

const email = ref("");
const password = ref("");
const submitting = ref(false);
const error = ref<string | null>(null);

async function onSubmit(): Promise<void> {
  submitting.value = true;
  error.value = null;

  try {
    await auth.register(email.value, password.value);
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

    <form @submit.prevent="onSubmit">
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
      <RouterLink to="/login">Log in</RouterLink>
    </p>
  </main>
</template>
