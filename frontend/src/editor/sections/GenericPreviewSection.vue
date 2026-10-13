<script setup lang="ts">
import {
  useEditorContext,
} from "../core/context";

const editor = useEditorContext();
</script>

<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">
        Preview
      </h2>
    </header>

    <pre class="mb-0">{{
      JSON.stringify(
        editor.record.value,
        null,
        2,
      )
    }}</pre>
  </section>
</template>
