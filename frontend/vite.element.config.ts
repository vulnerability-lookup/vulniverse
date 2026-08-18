import { resolve } from "node:path";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [
    vue({
      customElement: /\.ce\.vue$/,
    }),
  ],

  /*
   * Vite's library mode (build.lib below) deliberately leaves
   * process.env.NODE_ENV unreplaced, on the assumption a "library"
   * build gets re-bundled by a consumer's own tooling that defines
   * it. This bundle is loaded directly via a bare <script
   * type="module"> in a host page with no further bundling step
   * (e.g. embedded in vulnerability-lookup) — browsers have no
   * `process` global at all, so Vue's own runtime (which gates its
   * dev-only warnings behind this check) throws "process is not
   * defined" the moment it's loaded standalone.
   */
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },

  css: {
    preprocessorOptions: {
      scss: {
        quietDeps: true,
        silenceDeprecations: ['import'],
      },
    },
  },

  build: {
    lib: {
      entry: resolve(
        __dirname,
        "src/element.ts",
      ),
      formats: ["es"],
      fileName: () =>
        "vulniverse-editor.js",
    },

    outDir: "dist/element",
    emptyOutDir: true,
    sourcemap: true,

    assetsInlineLimit: 1_000_000,
  },
});
