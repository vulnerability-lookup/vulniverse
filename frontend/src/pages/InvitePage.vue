<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiRequest } from "@/repositories/apiRequest";
import { ApiError } from "@/shared/errors";
import { useAuthStore } from "@/stores/auth";

/*
 * Where an invitation link leads: what it offers, then joining (logged
 * in) or logging in / registering to join (logged out). Public route;
 * the token in the link is the secret.
 */

interface InvitationInfo {
  organisation: string;
  role: "admin" | "editor";
  state: "valid" | "accepted" | "revoked" | "expired";
}

const STATE_TEXT: Record<Exclude<InvitationInfo["state"], "valid">, string> = {
  accepted: "has already been used",
  revoked: "has been withdrawn",
  expired: "has expired",
};

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const token = computed(() => String(route.params.token));
const info = ref<InvitationInfo | null>(null);
const registration = ref<"open" | "invite" | "closed">("open");
const loading = ref(true);
const joining = ref(false);
const error = ref<string | null>(null);

const roleLabel = computed(() => (info.value?.role === "admin" ? "an admin" : "an editor"));

async function join(): Promise<void> {
  joining.value = true;
  error.value = null;

  try {
    await apiRequest(`/invitations/${encodeURIComponent(token.value)}/accept`, { method: "POST" });
    await auth.fetchMe();
    await router.replace({ name: "records" });
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : "Unable to join.";
  } finally {
    joining.value = false;
  }
}

onMounted(async () => {
  try {
    const [invitation, mode] = await Promise.all([
      apiRequest<InvitationInfo>(`/invitations/${encodeURIComponent(token.value)}`),
      apiRequest<{ mode: "open" | "invite" | "closed" }>("/auth/registration"),
    ]);
    info.value = invitation;
    registration.value = mode.mode;
  } catch (failure) {
    error.value = failure instanceof ApiError && failure.status === 404
      ? "This invitation link isn't valid. Check that you copied all of it."
      : failure instanceof Error ? failure.message : "Unable to load the invitation.";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <main
    class="container py-5"
    style="max-width: 560px;"
  >
    <h1 class="h3 mb-4">
      Invitation
    </h1>

    <p
      v-if="loading"
      class="text-secondary"
    >
      Loading…
    </p>

    <template v-else-if="info">
      <p
        v-if="info.state !== 'valid'"
        class="alert alert-warning"
        role="status"
      >
        This invitation to {{ info.organisation }} {{ STATE_TEXT[info.state] }}.
        Ask its admins for a new link.
      </p>

      <template v-else>
        <p class="lead">
          You're invited to join <strong>{{ info.organisation }}</strong> as {{ roleLabel }}.
        </p>
        <p class="text-secondary">
          Members share the organisation's vulnerability records, drafts included.
        </p>

        <div
          v-if="error"
          class="alert alert-danger"
          role="alert"
        >
          {{ error }}
        </div>

        <div
          v-if="auth.isAuthenticated"
          class="d-flex align-items-center gap-3"
        >
          <button
            type="button"
            class="btn btn-primary"
            :disabled="joining"
            @click="join"
          >
            Join {{ info.organisation }}
          </button>
          <span class="text-secondary small">as {{ auth.currentUser?.email }}</span>
        </div>

        <div
          v-else
          class="d-flex flex-wrap gap-2"
        >
          <RouterLink
            class="btn btn-primary"
            :to="{ name: 'login', query: { redirect: route.fullPath } }"
          >
            Log in to join
          </RouterLink>
          <RouterLink
            v-if="registration !== 'closed'"
            class="btn btn-outline-primary"
            :to="{ name: 'register', query: { invite: token } }"
          >
            Create an account
          </RouterLink>
        </div>
      </template>
    </template>

    <div
      v-else-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}
    </div>
  </main>
</template>
