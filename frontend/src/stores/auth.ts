import { ref, computed } from "vue";
import { defineStore } from "pinia";

import { clearCsrfToken } from "@/repositories/csrf";
import { apiRequest } from "@/repositories/apiRequest";
import { ApiError } from "@/shared/errors";

export type AuthMode = "local" | "multiuser";

export interface AuthOrganisation {
  id: number;
  name: string;
  role: "admin" | "editor";
}

export interface AuthUser {
  id: number;
  email: string;
  isAdmin: boolean;
  authMode: AuthMode;
  organisations: AuthOrganisation[];
  /** Where new records go and which records the list shows; null
   * without any organisation. */
  currentOrganisationId: number | null;
  /** [server] two_factor: required for every account; enabled once set up. */
  twoFactor: { required: boolean; enabled: boolean };
}

export interface TwoFactorSetup {
  secret: string;
  /** otpauth:// URI, for the QR code. */
  uri: string;
}

export const useAuthStore = defineStore("auth", () => {
  const currentUser = ref<AuthUser | null>(null);
  // Distinguishes "haven't checked yet" from "checked, not logged in" —
  // the router guard needs this to avoid bouncing to /login on the very
  // first page load before fetchMe() has resolved.
  const initialized = ref(false);

  const isAuthenticated = computed(() => currentUser.value !== null);

  const isLocalMode = computed(
    () => currentUser.value?.authMode === "local",
  );

  // Until it's set up, the backend refuses everything else.
  const needsTwoFactorSetup = computed(
    () => currentUser.value?.twoFactor.required === true && !currentUser.value.twoFactor.enabled,
  );

  const currentOrganisation = computed(
    () => currentUser.value?.organisations.find(
      (organisation) => organisation.id === currentUser.value?.currentOrganisationId,
    ) ?? null,
  );

  async function fetchMe(): Promise<void> {
    try {
      currentUser.value = await apiRequest<AuthUser>("/auth/me");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        currentUser.value = null;
      } else {
        throw error;
      }
    } finally {
      initialized.value = true;
    }
  }

  /** "code": the password was right, now loginCode() with the 2FA code. */
  async function login(email: string, password: string): Promise<"done" | "code"> {
    const response = await apiRequest<AuthUser | { twoFactorRequired: true }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if ("twoFactorRequired" in response) return "code";
    currentUser.value = response;
    return "done";
  }

  async function loginCode(code: string): Promise<void> {
    currentUser.value = await apiRequest<AuthUser>("/auth/login/two-factor", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  }

  function startTwoFactorSetup(): Promise<TwoFactorSetup> {
    return apiRequest<TwoFactorSetup>("/auth/two-factor/setup", { method: "POST" });
  }

  async function finishTwoFactorSetup(code: string): Promise<void> {
    currentUser.value = await apiRequest<AuthUser>("/auth/two-factor", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  }

  /** With an invitation link's token, the account joins its organisation. */
  async function register(email: string, password: string, invitation?: string): Promise<void> {
    currentUser.value = await apiRequest<AuthUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, invitation }),
    });
  }

  async function switchOrganisation(id: number): Promise<void> {
    currentUser.value = await apiRequest<AuthUser>("/auth/organisation", {
      method: "POST",
      body: JSON.stringify({ id }),
    });
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiRequest("/auth/password", {
      method: "POST",
      body: JSON.stringify({ currentPassword, newPassword }),
    });
  }

  /** Deletes the account (the backend also ends the session). */
  async function deleteAccount(password: string): Promise<void> {
    await apiRequest("/auth/account", {
      method: "DELETE",
      body: JSON.stringify({ password }),
    });
    currentUser.value = null;
    clearCsrfToken();
  }

  async function logout(): Promise<void> {
    await apiRequest("/auth/logout", { method: "POST" });
    currentUser.value = null;
    clearCsrfToken();
  }

  return {
    currentUser,
    initialized,
    isAuthenticated,
    isLocalMode,
    currentOrganisation,
    needsTwoFactorSetup,
    fetchMe,
    loginCode,
    startTwoFactorSetup,
    finishTwoFactorSetup,
    switchOrganisation,
    changePassword,
    deleteAccount,
    login,
    register,
    logout,
  };
});
