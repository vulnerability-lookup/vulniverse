<script setup lang="ts">
import {
  computed,
  nextTick,
  ref,
} from "vue";

import {
  useEditorContext,
} from "../core/context";

import {
  MAX_TEXT,
  layoutTree,
  recordTree,
  type PlacedNode,
  type TreeNode,
} from "../core/record-tree";

import {
  isWithin,
} from "../core/reveal";

import {
  DEFAULT_PROFILE_ID,
  getEditorProfile,
} from "../profiles";

/*
 * The record as a graph, left to right: click a circle to open or close
 * a field's children, click a name to show the field in the Editor
 * section (its tab, opened cards, scrolled to and focused).
 */
const editor = useEditorContext();

const profile = computed(() => getEditorProfile(editor.profile.value ?? DEFAULT_PROFILE_ID));

const root = computed<TreeNode>(() => ({
  path: "",
  label: `${profile.value.label} record`,
  summary: "",
  kind: "object",
  required: false,
  children: recordTree(editor.record.value, profile.value.schema),
}));

// The record and its first two levels start open.
const START_OPEN_DEPTH = 3;
const open = ref<Set<string> | null>(null);

function initialOpen(node: TreeNode, depth: number, into: Set<string>): Set<string> {
  if (depth < START_OPEN_DEPTH && node.children.length) {
    into.add(node.path);
    node.children.forEach((child) => initialOpen(child, depth + 1, into));
  }

  return into;
}

// Until the user opens or closes something, the start set.
const openPaths = computed(() => open.value ?? initialOpen(root.value, 0, new Set()));

const layout = computed(() => layoutTree(root.value, openPaths.value));

function link({ from, to }: { from: PlacedNode; to: PlacedNode }): string {
  const middle = (from.x + to.x) / 2;

  return `M${from.x},${from.y} C${middle},${from.y} ${middle},${to.y} ${to.x},${to.y}`;
}

function issue(path: string): "error" | "warning" | null {
  const within = editor.validationErrors.value.filter(
    (error) => isWithin(error.path.join("."), path),
  );

  if (within.some((error) => (error.severity ?? "error") === "error")) return "error";

  return within.length ? "warning" : null;
}

function clip(text: string): string {
  return text.length > MAX_TEXT ? `${text.slice(0, MAX_TEXT - 1)}…` : text;
}

const scroller = ref<HTMLElement | null>(null);

async function toggle(node: TreeNode): Promise<void> {
  if (!node.children.length) {
    if (node.path) editor.revealPath(node.path);
    return;
  }

  const paths = new Set(openPaths.value);
  const opening = !paths.delete(node.path);

  if (opening) paths.add(node.path);
  open.value = paths;

  if (opening) {
    // Bring the new children into view; they may lie right of or below it.
    await nextTick();
    const middle = node.children[Math.floor(node.children.length / 2)]!;
    scroller.value
      ?.querySelector(`[data-tree-path="${CSS.escape(middle.path)}"]`)
      ?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  }
}
</script>

<template>
  <section>
    <header class="mb-3">
      <h2 class="h4">
        Tree
      </h2>

      <p class="text-secondary mb-2">
        The record as currently edited. Click a circle to open or close a
        field, click a name to show it in the editor.
      </p>

      <ul
        class="record-graph-legend list-inline small text-secondary mb-0"
        aria-hidden="true"
      >
        <li class="list-inline-item is-object">
          <svg viewBox="-7 -7 14 14"><circle r="5" /></svg>Object
        </li>
        <li class="list-inline-item is-array">
          <svg viewBox="-7 -7 14 14"><circle r="5" /></svg>List
        </li>
        <li class="list-inline-item is-value">
          <svg viewBox="-7 -7 14 14"><circle r="5" /></svg>Value
        </li>
        <li class="list-inline-item is-object is-closed">
          <svg viewBox="-7 -7 14 14"><circle r="5" /></svg>Closed
        </li>
        <li class="list-inline-item">
          <strong>Bold *</strong> required
        </li>
        <li class="list-inline-item is-error">
          <svg viewBox="-7 -7 14 14"><circle
            class="record-graph-halo"
            r="6"
          /></svg>Has errors
        </li>
      </ul>
    </header>

    <div
      v-if="root.children.length"
      ref="scroller"
      class="record-graph"
    >
      <svg
        :width="layout.width"
        :height="layout.height"
        role="tree"
        aria-label="Record tree"
      >
        <path
          v-for="item in layout.links"
          :key="item.to.node.path"
          class="record-graph-link"
          :d="link(item)"
        />

        <g
          v-for="placed in layout.nodes"
          :key="placed.node.path || 'root'"
          :transform="`translate(${placed.x},${placed.y})`"
          :data-tree-path="placed.node.path"
          role="treeitem"
          :aria-expanded="placed.node.children.length ? placed.open : undefined"
          :class="[
            'record-graph-node',
            `is-${placed.node.kind}`,
            {
              'is-closed': placed.node.children.length && !placed.open,
              [`is-${issue(placed.node.path)}`]: issue(placed.node.path),
            },
          ]"
        >
          <title>{{ placed.node.path || "record" }}{{ placed.node.summary ? `: ${placed.node.summary}` : "" }}</title>

          <g
            class="record-graph-dot"
            role="button"
            tabindex="0"
            :aria-label="placed.node.children.length
              ? `${placed.open ? 'Close' : 'Open'} ${placed.node.label}`
              : `Show ${placed.node.label} in the editor`"
            @click="toggle(placed.node)"
            @keydown.enter.space.prevent="toggle(placed.node)"
          >
            <circle
              class="record-graph-hit"
              r="11"
            />
            <circle
              v-if="issue(placed.node.path)"
              class="record-graph-halo"
              r="8.5"
            />
            <circle r="5" />
          </g>

          <text
            :x="placed.labelLeft ? -11 : 11"
            :y="placed.node.summary && !placed.open ? -2 : 4"
            :text-anchor="placed.labelLeft ? 'end' : 'start'"
            :class="['record-graph-label', { 'is-required': placed.node.required, 'is-link': placed.node.path }]"
            :role="placed.node.path ? 'link' : undefined"
            :tabindex="placed.node.path ? 0 : undefined"
            @click="placed.node.path && editor.revealPath(placed.node.path)"
            @keydown.enter.prevent="placed.node.path && editor.revealPath(placed.node.path)"
          >
            {{ clip(placed.node.label) }}{{ placed.node.required ? " *" : "" }}
          </text>

          <text
            v-if="placed.node.summary && !placed.open"
            :x="placed.labelLeft ? -11 : 11"
            y="11"
            :text-anchor="placed.labelLeft ? 'end' : 'start'"
            class="record-graph-value"
          >
            {{ clip(placed.node.summary) }}
          </text>
        </g>
      </svg>
    </div>

    <p
      v-else
      class="text-secondary"
    >
      The record is empty.
    </p>
  </section>
</template>
