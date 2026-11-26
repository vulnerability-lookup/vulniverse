<script setup lang="ts">
import {
  ICONS,
} from "../icons";

const VERSION = __VULNIVERSE_VERSION__;

interface NavigationItem {
  id: string;
  label: string;
  // Path data for a 16×16 line icon (see icons.ts).
  icon?: string;
}

withDefaults(
  defineProps<{
    modelValue: string;
    items: NavigationItem[];
    panelItems?: NavigationItem[];
    // Only the icons are shown; labels stay for screen readers and tooltips.
    collapsed?: boolean;
  }>(),
  {
    panelItems: () => [],
    collapsed: false,
  },
);

defineEmits<{
  "update:modelValue": [
    value: string,
  ];
  "update:collapsed": [
    value: boolean,
  ];
}>();
</script>

<template>
  <nav
    class="nav nav-pills flex-column editor-sidebar"
    :class="{ 'is-collapsed': collapsed }"
    aria-label="Editor sections"
  >
    <button
      type="button"
      class="btn btn-sm editor-sidebar-toggle"
      :aria-expanded="!collapsed"
      :aria-label="collapsed ? 'Expand the sidebar' : 'Collapse the sidebar'"
      :title="collapsed ? 'Expand the sidebar' : 'Collapse the sidebar'"
      @click="$emit('update:collapsed', !collapsed)"
    >
      <svg
        class="editor-sidebar-icon"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      ><path :d="ICONS.collapse" /></svg>
    </button>

    <template
      v-for="(group, groupIndex) in [items, panelItems]"
      :key="groupIndex"
    >
      <template v-if="group.length">
        <template v-if="groupIndex === 1">
          <hr class="editor-sidebar-divider">

          <div
            v-if="!collapsed"
            class="editor-sidebar-heading text-secondary text-uppercase"
          >
            Panels
          </div>
        </template>

        <button
          v-for="item in group"
          :key="item.id"
          type="button"
          class="nav-link text-start"
          :class="{
            active: modelValue === item.id,
          }"
          :title="collapsed ? item.label : undefined"
          :aria-current="modelValue === item.id ? 'page' : undefined"
          @click="
            $emit(
              'update:modelValue',
              item.id,
            )
          "
        >
          <svg
            v-if="item.icon"
            class="editor-sidebar-icon"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          ><path :d="item.icon" /></svg>

          <span :class="{ 'visually-hidden': collapsed }">{{ item.label }}</span>
        </button>
      </template>
    </template>

    <a
      v-if="!collapsed"
      class="editor-sidebar-version small text-secondary"
      :href="`https://github.com/vulnerability-lookup/vulniverse/releases/tag/v${VERSION}`"
      target="_blank"
      rel="noopener"
    >Vulniverse v{{ VERSION }}</a>
  </nav>
</template>
