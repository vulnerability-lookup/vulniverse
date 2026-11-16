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
  ancestorPaths,
  layoutTree,
  recordTree,
  searchTree,
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

// Scrolls only the graph's box (scrollIntoView would move the page too).
function scrollTo(path: string, always: boolean): void {
  const box = scroller.value;
  const node = box?.querySelector(`[data-tree-path="${CSS.escape(path)}"]`);

  if (!box || !node) return;

  const outer = box.getBoundingClientRect();
  const inner = node.getBoundingClientRect();
  const visible = inner.left >= outer.left && inner.right <= outer.right
    && inner.top >= outer.top && inner.bottom <= outer.bottom;

  if (always || !visible) {
    box.scrollTo({
      left: box.scrollLeft + inner.left - outer.left + (inner.width - outer.width) / 2,
      top: box.scrollTop + inner.top - outer.top + (inner.height - outer.height) / 2,
      behavior: "smooth",
    });
  }
}

/*
 * Search: every field whose name or value contains the query counts,
 * open or not. Stepping to a match opens the nodes above it, so only
 * the matches looked at get opened, not all of them at once.
 */
const query = ref("");
const matches = computed(() => searchTree(root.value, query.value));
const matchPaths = computed(() => new Set(matches.value.map((node) => node.path)));
const current = ref(-1);

async function step(by: number): Promise<void> {
  const count = matches.value.length;

  if (!count) return;

  current.value = current.value < 0 && by < 0
    ? count - 1
    : (current.value + by + count) % count;

  const path = matches.value[current.value]!.path;
  open.value = new Set([...openPaths.value, ...ancestorPaths(path)]);

  await nextTick();
  scrollTo(path, true);
}

function search(value: string): void {
  query.value = value;
  current.value = -1;
}

const currentPath = computed(() => matches.value[current.value]?.path ?? null);

/*
 * Zoom scales the drawing, so the box scrolls over the scaled size.
 * Ctrl + wheel zooms around the mouse, the buttons around the middle.
 */
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2;
const zoom = ref(1);

async function zoomTo(value: number, anchor?: { x: number; y: number }): Promise<void> {
  const box = scroller.value;
  const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100));

  if (!box || next === zoom.value) return;

  const at = anchor ?? { x: box.clientWidth / 2, y: box.clientHeight / 2 };
  const point = { x: (box.scrollLeft + at.x) / zoom.value, y: (box.scrollTop + at.y) / zoom.value };

  zoom.value = next;
  await nextTick();
  box.scrollLeft = point.x * next - at.x;
  box.scrollTop = point.y * next - at.y;
}

function fit(): void {
  const box = scroller.value;

  if (box) {
    const scale = Math.min(1, box.clientWidth / layout.value.width, box.clientHeight / layout.value.height);
    // Rounded down, so the fitted graph never overflows by a pixel.
    void zoomTo(Math.floor(scale * 100) / 100);
  }
}

function wheel(event: WheelEvent): void {
  if (!event.ctrlKey) return;

  event.preventDefault();
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
  void zoomTo(zoom.value * (event.deltaY < 0 ? 1.1 : 1 / 1.1), {
    x: event.clientX - box.left,
    y: event.clientY - box.top,
  });
}

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
    scrollTo(node.children[Math.floor(node.children.length / 2)]!.path, false);
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
      class="record-graph-toolbar d-flex flex-wrap gap-2 mb-2"
    >
      <div class="input-group input-group-sm record-graph-search">
        <input
          :value="query"
          type="search"
          class="form-control"
          placeholder="Search names and values"
          aria-label="Search the tree"
          @input="search(($event.target as HTMLInputElement).value)"
          @keydown.enter.prevent="step($event.shiftKey ? -1 : 1)"
        >
        <span
          v-if="query.trim()"
          class="input-group-text"
          aria-live="polite"
        >
          {{ matches.length ? `${current < 0 ? "–" : current + 1} / ${matches.length}` : "No matches" }}
        </span>
        <button
          type="button"
          class="btn btn-outline-secondary"
          aria-label="Previous match"
          :disabled="!matches.length"
          @click="step(-1)"
        >
          ↑
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          aria-label="Next match"
          :disabled="!matches.length"
          @click="step(1)"
        >
          ↓
        </button>
      </div>

      <div
        class="btn-group btn-group-sm ms-auto"
        role="group"
        aria-label="Zoom"
      >
        <button
          type="button"
          class="btn btn-outline-secondary"
          aria-label="Zoom out"
          :disabled="zoom <= MIN_ZOOM"
          @click="zoomTo(zoom / 1.25)"
        >
          −
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary record-graph-zoom"
          title="Reset to 100%"
          @click="zoomTo(1)"
        >
          {{ Math.round(zoom * 100) }}%
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          aria-label="Zoom in"
          :disabled="zoom >= MAX_ZOOM"
          @click="zoomTo(zoom * 1.25)"
        >
          +
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          title="Fit the open part of the tree in the box"
          @click="fit"
        >
          Fit
        </button>
      </div>
    </div>

    <div
      v-if="root.children.length"
      ref="scroller"
      class="record-graph"
      @wheel="wheel"
    >
      <svg
        :width="layout.width * zoom"
        :height="layout.height * zoom"
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
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
              'is-match': matchPaths.has(placed.node.path),
              'is-current-match': placed.node.path === currentPath,
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
              v-if="placed.node.path === currentPath"
              class="record-graph-found"
              r="12"
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
