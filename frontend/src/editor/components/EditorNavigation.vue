<script setup lang="ts">
interface NavigationItem {
  id: string;
  label: string;
}

withDefaults(
  defineProps<{
    modelValue: string;
    items: NavigationItem[];
    panelItems?: NavigationItem[];
  }>(),
  {
    panelItems: () => [],
  },
);

defineEmits<{
  "update:modelValue": [
    value: string,
  ];
}>();
</script>

<template>
  <nav
    class="nav nav-pills flex-column editor-sidebar"
    aria-label="Editor sections"
  >
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="nav-link text-start"
      :class="{
        active: modelValue === item.id,
      }"
      @click="
        $emit(
          'update:modelValue',
          item.id,
        )
      "
    >
      {{ item.label }}
    </button>

    <template v-if="panelItems.length">
      <hr class="editor-sidebar-divider">

      <div class="editor-sidebar-heading text-secondary text-uppercase">
        Modules
      </div>

      <button
        v-for="item in panelItems"
        :key="item.id"
        type="button"
        class="nav-link text-start"
        :class="{
          active: modelValue === item.id,
        }"
        @click="
          $emit(
            'update:modelValue',
            item.id,
          )
        "
      >
        {{ item.label }}
      </button>
    </template>
  </nav>
</template>
