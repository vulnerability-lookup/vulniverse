import type {
  LifecycleTransition,
} from "../contracts";

/*
 * The standalone app's own draft/publish pair — used whenever a
 * repository doesn't declare EditorRepository.lifecycleTransitions
 * itself (see useEditorExtensions). Encodes exactly the behavior
 * EditorHeader.vue used to hardcode directly: Publish only while a
 * draft, Revert to draft only once published.
 */
export const DEFAULT_LIFECYCLE_TRANSITIONS: LifecycleTransition[] = [
  {
    id: "publish",
    label: "Publish",
    targetIsDraft: false,
    isVisible: (context) => context.isDraft,
  },
  {
    id: "unpublish",
    label: "Revert to draft",
    targetIsDraft: true,
    isVisible: (context) => !context.isDraft,
  },
];
