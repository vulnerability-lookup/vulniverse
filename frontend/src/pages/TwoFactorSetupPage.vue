<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { renderSVG } from "uqr";

import { useAuthStore, type TwoFactorSetup } from "@/stores/auth";

/*
 * Setting up two-factor authentication ([server] two_factor), which
 * every account must do before anything else (backend: api/auth.py,
 * services/two_factor.py). A lost device: an admin resets it.
 */

const auth = useAuthStore();
const router = useRouter();

const setup = ref<TwoFactorSetup | null>(null);
const code = ref("");
const busy = ref(false);
const error = ref<string | null>(null);

// An <img> of the SVG: no v-html needed, and always black on white.
const qrSource = computed(() => setup.value
  ? `data:image/svg+xml;utf8,${encodeURIComponent(renderSVG(setup.value.uri))}`
  : "");

// The secret in groups of four, easier to type by hand.
const groupedSecret = computed(() => setup.value?.secret.match(/.{1,4}/g)?.join(" ") ?? "");

async function confirm(): Promise<void> {
  busy.value = true;
  error.value = null;

  try {
    await auth.finishTwoFactorSetup(code.value);
    await router.replace("/records");
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "That didn't work.";
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  if (auth.currentUser?.twoFactor.enabled) {
    await router.replace("/account");
    return;
  }

  try {
    setup.value = await auth.startTwoFactorSetup();
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "Unable to start the setup.";
  }
});
</script>

<template>
  <main
    class="container py-5"
    style="max-width: 560px;"
  >
    <h1 class="h3 mb-1">
      Set up two-factor authentication
    </h1>
    <p class="text-secondary mb-4">
      This instance asks for a code from an authenticator app (such as
      Aegis, Google Authenticator or 1Password) at every login, in addition
      to your password.
    </p>

    <div
      v-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}
    </div>

    <form
      v-if="setup"
      class="card card-body"
      @submit.prevent="confirm"
    >
      <ol class="ps-3 mb-3">
        <li class="mb-3">
          Scan this code with your app:
          <img
            :src="qrSource"
            alt="QR code for your authenticator app"
            class="d-block my-2 border rounded"
            width="200"
            height="200"
          >
          <span class="small text-secondary">
            Can't scan it? Enter this key instead:
            <code class="user-select-all">{{ groupedSecret }}</code>
          </span>
        </li>
        <li>
          <label
            for="two-factor-code"
            class="form-label"
          >Enter the 6-digit code it shows:</label>
          <input
            id="two-factor-code"
            v-model="code"
            class="form-control"
            style="max-width: 12rem;"
            inputmode="numeric"
            autocomplete="one-time-code"
            pattern="[0-9 ]{6,7}"
            required
          >
        </li>
      </ol>

      <div>
        <button
          type="submit"
          class="btn btn-primary"
          :disabled="busy"
        >
          Turn on
        </button>
      </div>
    </form>

    <p class="mt-3 small text-secondary">
      If you lose the device, an admin of this instance can reset it.
    </p>
  </main>
</template>
