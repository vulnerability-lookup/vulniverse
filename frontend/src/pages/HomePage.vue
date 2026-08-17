<template>
  <main class="container py-5">
    <h1>Vulniverse</h1>

    <p>
      <RouterLink
        to="/editor/new"
        class="btn btn-primary"
      >
        Create new record
      </RouterLink>
    </p>

    <p>
      Or open an existing vulnerability record by navigating to:
    </p>

    <code>
      /editor/CVE-2026-99999
    </code>
  </main>
</template>
