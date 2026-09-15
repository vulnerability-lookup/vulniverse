import {
  createRouter,
  createWebHistory,
} from "vue-router";

import LandingPage from
  "@/pages/LandingPage.vue";

import TryEditorPage from
  "@/pages/TryEditorPage.vue";

import RecordsPage from
  "@/pages/RecordsPage.vue";

import EditorPage from
  "@/pages/EditorPage.vue";

import NewRecordPage from
  "@/pages/NewRecordPage.vue";

import LoginPage from
  "@/pages/LoginPage.vue";

import RegisterPage from
  "@/pages/RegisterPage.vue";

import CnaCredentialsPage from
  "@/pages/CnaCredentialsPage.vue";

import AdminUsersPage from
  "@/pages/AdminUsersPage.vue";

import { useAuthStore } from "@/stores/auth";

export const router = createRouter({
  history: createWebHistory(
    import.meta.env.BASE_URL,
  ),

  routes: [
    {
      path: "/",
      name: "landing",
      component: LandingPage,
      meta: { public: true },
    },
    {
      path: "/try",
      name: "try",
      component: TryEditorPage,
      meta: { public: true },
    },
    {
      path: "/records",
      name: "records",
      component: RecordsPage,
    },
    {
      path: "/login",
      name: "login",
      component: LoginPage,
      meta: { public: true, guestOnly: true },
    },
    {
      path: "/register",
      name: "register",
      component: RegisterPage,
      meta: { public: true, guestOnly: true },
    },
    {
      path: "/cna-credentials",
      name: "cna-credentials",
      component: CnaCredentialsPage,
    },
    {
      path: "/admin/users",
      name: "admin-users",
      component: AdminUsersPage,
      meta: { adminOnly: true },
    },
    {
      path: "/editor/new",
      name: "editor-new",
      component: NewRecordPage,
    },
    {
      path: "/editor/:recordId",
      name: "editor",
      component: EditorPage,
      props: false,
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (!auth.initialized) {
    await auth.fetchMe();
  }

  if (!to.meta.public && !auth.isAuthenticated) {
    return {
      name: "login",
      query: { redirect: to.fullPath },
    };
  }

  // Only login/register bounce an already-authenticated visitor away —
  // the landing page and the sandbox editor are public for everyone,
  // logged in or not, unlike login/register which stop making sense
  // once you're already signed in.
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: "records" };
  }

  if (to.meta.adminOnly && !auth.currentUser?.isAdmin) {
    return { name: "records" };
  }

  return true;
});
