import { ref, computed } from "vue";
import { defineStore } from "pinia";

import { clearCsrfToken } from "@/repositories/csrf";
import { apiRequest } from "@/repositories/apiRequest";
import { RepositoryError } from "@/repositories/RepositoryError";

export interface AuthUser {
  id: number;
  email: string;
  isAdmin: boolean;
}

export const useAuthStore = defineStore("auth", () => {
  const currentUser = ref<AuthUser | null>(null);
  // Distinguishes "haven't checked yet" from "checked, not logged in" —
  // the router guard needs this to avoid bouncing to /login on the very
  // first page load before fetchMe() has resolved.
  const initialized = ref(false);

  const isAuthenticated = computed(() => currentUser.value !== null);

  async function fetchMe(): Promise<void> {
    try {
      currentUser.value = await apiRequest<AuthUser>("/auth/me");
    } catch (error) {
      if (error instanceof RepositoryError && error.status === 401) {
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

  async function register(email: string, password: string): Promise<void> {
    currentUser.value = await apiRequest<AuthUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
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
    fetchMe,
    login,
    register,
    logout,
  };
});
