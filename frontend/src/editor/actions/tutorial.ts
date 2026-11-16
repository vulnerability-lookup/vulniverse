import type {
  EditorAction,
} from "../contracts";

/**
 * Starts the editor's guided tutorial (tutorial/EditorTutorial.vue). Optional like
 * any action: a host lists it in VulniverseEditor's `actions` to offer
 * it, the standalone app through [actions] "tutorial" in its config.
 */
export const tutorialAction: EditorAction = {
  id: "tutorial",
  label: "Tutorial",
  // A question mark in a circle.
  icon: "M8 14.5A6.5 6.5 0 1 0 8 1.5a6.5 6.5 0 0 0 0 13ZM6.1 6.2a1.9 1.9 0 1 1 2.7 1.7c-.5.3-.8.7-.8 1.2v.4M8 11.6v.01",

  isVisible: (context) => Boolean(context.startTutorial),

  async run(context) {
    context.startTutorial?.();
  },
};
