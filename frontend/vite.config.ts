import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    vueDevTools(),
  ],


  base: mode === 'github-pages' ? '/vulniverse/' : '/',

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  css: {
    preprocessorOptions: {
      scss: {
        // Bootstrap's own SCSS still uses Sass APIs that Dart Sass
        // deprecates; quietDeps silences warnings from dependencies
        quietDeps: true,
        silenceDeprecations: ['import'],
      },
    },
  },

  server: {
    port: 5173,

    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
}))
