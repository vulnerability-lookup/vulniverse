import {
  createRouter,
  createWebHistory,
} from "vue-router";

import EditorPage from
  "@/pages/EditorPage.vue";

import HomePage from
  "@/pages/HomePage.vue";

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
      name: "home",
      component: HomePage,
    },
    {
      path: "/login",
      name: "login",
      component: LoginPage,
      meta: { public: true },
    },
    {
      path: "/register",
      name: "register",
      component: RegisterPage,
      meta: { public: true },
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

  if (to.meta.public && auth.isAuthenticated) {
    return { name: "home" };
  }

  if (to.meta.adminOnly && !auth.currentUser?.isAdmin) {
    return { name: "home" };
  }

  return true;
});
