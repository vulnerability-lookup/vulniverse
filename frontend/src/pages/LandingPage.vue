<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import vulniverseLogo from "@/assets/vulniverse-logo.png";

const auth = useAuthStore();
</script>

<template>
  <main class="container py-5">
    <div class="row justify-content-center text-center mb-5">
      <div class="col-lg-8">
        <img
          :src="vulniverseLogo"
          alt="Vulniverse"
          class="mb-4"
        >

        <p class="lead text-secondary">
          An editor for vulnerability records in the CVE and GCVE
          formats — validated against the real published schemas as
          you type, with support for reserving and publishing
          identifiers directly to a CVE Program instance or a
          Vulnerability-Lookup deployment.
        </p>

        <div class="d-flex flex-wrap justify-content-center gap-2 mt-4">
          <RouterLink to="/try" class="btn btn-primary btn-lg">
            Try the editor
          </RouterLink>

          <RouterLink
            v-if="!auth.isAuthenticated"
            to="/register"
            class="btn btn-outline-secondary btn-lg"
          >
            Create an account
          </RouterLink>

          <RouterLink
            v-else
            to="/records"
            class="btn btn-outline-secondary btn-lg"
          >
            Go to your records
          </RouterLink>
        </div>
      </div>
    </div>

    <div class="row g-4">
      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h5">CVE &amp; GCVE, one editor</h2>
            <p class="text-secondary mb-0">
              Author a plain CVE Record Format 5.2.0 record, or extend
              it with the GCVE-BCP-05 <code>x_gcve</code> extension —
              the same form, the same validation, either way.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h5">Reserve and publish</h2>
            <p class="text-secondary mb-0">
              Reserve a real identifier from a CVE Program instance or
              a Vulnerability-Lookup deployment, then publish straight
              from the editor — your credentials, stored per-account.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-4">
        <div class="card h-100">
          <div class="card-body">
            <h2 class="h5">Embeddable</h2>
            <p class="text-secondary mb-0">
              The same editor ships as a <code>&lt;vulniverse-editor&gt;</code>
              web component — any host with its own backend can embed
              it directly, as Vulnerability-Lookup itself does.
            </p>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
