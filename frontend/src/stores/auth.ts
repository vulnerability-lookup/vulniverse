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

  async function login(email: string, password: string): Promise<void> {
    currentUser.value = await apiRequest<AuthUser>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
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
    fetchMe,
    switchOrganisation,
    changePassword,
    deleteAccount,
    login,
    register,
    logout,
  };
});
