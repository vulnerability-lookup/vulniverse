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
