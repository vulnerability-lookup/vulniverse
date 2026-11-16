<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  ref,
} from "vue";

import type {
  TutorialStep,
} from "./steps";

/*
 * A guided tutorial through the editor: dims everything but the current
 * step's element and explains it in a small box next to it. Drawn
 * inside the editor (its shadow root, when embedded), so it needs no
 * styles in the host page.
 */
const props = defineProps<{
  steps: TutorialStep[];
}>();

const emit = defineEmits<{
  // Show this section before the step (the editor switches to it).
  section: [id: string];
  end: [];
}>();

const host = ref<HTMLElement | null>(null);
const popover = ref<HTMLElement | null>(null);
const open = ref(false);
const index = ref(0);
const rect = ref<DOMRect | null>(null);
let target: HTMLElement | null = null;

const step = computed(() => props.steps[index.value]);
const isLast = computed(() => index.value === props.steps.length - 1);

const frame = () => new Promise((done) => requestAnimationFrame(done));

function measure(): void {
  rect.value = target?.getBoundingClientRect() ?? null;
}

/** Shows step `from`, or the next one that exists in direction `by`. */
async function show(from: number, by: 1 | -1): Promise<void> {
  const root = host.value?.closest(".vulniverse-editor");

  for (let at = from; at >= 0 && at < props.steps.length; at += by) {
    const candidate = props.steps[at]!;

    if (candidate.section) {
      emit("section", candidate.section);
      // The section renders on the next ticks.
      await nextTick();
      await frame();
    }

    const element = candidate.target ? root?.querySelector<HTMLElement>(candidate.target) : null;

    if (candidate.target && !element) {
      continue;
    }

    index.value = at;
    target = element ?? null;
    target?.scrollIntoView({ block: "nearest", inline: "nearest" });
    measure();
    await nextTick();
    popover.value?.focus();
    return;
  }

  // Ran past the last step that exists.
  if (by === 1) end();
}

function start(): void {
  open.value = true;
  window.addEventListener("resize", measure);
  window.addEventListener("scroll", measure, true);
  window.addEventListener("keydown", onKey);
  void show(0, 1);
}

function end(): void {
  if (!open.value) return;

  open.value = false;
  target = null;
  window.removeEventListener("resize", measure);
  window.removeEventListener("scroll", measure, true);
  window.removeEventListener("keydown", onKey);
  emit("end");
}

function next(): void {
  if (isLast.value) end();
  else void show(index.value + 1, 1);
}

function back(): void {
  void show(index.value - 1, -1);
}

function onKey(event: KeyboardEvent): void {
  if (event.key === "Escape") end();
  else if (event.key === "ArrowRight") next();
  else if (event.key === "ArrowLeft" && index.value > 0) back();
  else return;

  event.preventDefault();
}

onBeforeUnmount(end);

const PAD = 6;
const GAP = 12;
const WIDTH = 320;
// Room the box needs above or below its element.
const ROOM = 200;

const spotlightStyle = computed(() => {
  const box = rect.value;

  return box && {
    top: `${box.top - PAD}px`,
    left: `${box.left - PAD}px`,
    width: `${box.width + 2 * PAD}px`,
    height: `${box.height + 2 * PAD}px`,
  };
});

// Below the element if there's room, else above, else over its bottom.
const popoverStyle = computed(() => {
  const box = rect.value;

  if (!box) return { top: "50%", left: "50%", transform: "translate(-50%, -50%)" };

  const left = `${Math.max(16, Math.min(box.left, window.innerWidth - WIDTH - 16))}px`;

  if (window.innerHeight - box.bottom > ROOM) return { left, top: `${box.bottom + GAP}px` };
  if (box.top > ROOM) return { left, bottom: `${window.innerHeight - box.top + GAP}px` };

  return { left, bottom: "16px" };
});

defineExpose({
  start,
});
</script>

<template>
  <div
    ref="host"
    class="editor-tutorial"
  >
    <template v-if="open && step">
      <div
        :class="spotlightStyle ? 'editor-tutorial-spotlight' : 'editor-tutorial-backdrop'"
        :style="spotlightStyle ?? undefined"
        aria-hidden="true"
      />

      <div
        ref="popover"
        class="editor-tutorial-popover card shadow"
        role="dialog"
        aria-labelledby="editor-tutorial-title"
        aria-describedby="editor-tutorial-text"
        tabindex="-1"
        :style="popoverStyle"
      >
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
            <h2
              id="editor-tutorial-title"
              class="h6 mb-0"
            >
              {{ step.title }}
            </h2>

            <button
              type="button"
              class="btn-close"
              aria-label="End tutorial"
              @click="end"
            />
          </div>

          <p
            id="editor-tutorial-text"
            class="small mb-3"
          >
            {{ step.text }}
          </p>

          <div class="d-flex justify-content-end gap-2">
            <button
              v-if="index > 0"
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="back"
            >
              Back
            </button>

            <button
              type="button"
              class="btn btn-sm btn-primary"
              @click="next"
            >
              {{ isLast ? "Done" : "Next" }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
