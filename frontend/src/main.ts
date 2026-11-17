// First: sets the page's theme before anything draws.
import "./theme"

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { router } from './router'

import "@jsonforms/vue-vanilla/vanilla.css"
import "./assets/main.scss"

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
