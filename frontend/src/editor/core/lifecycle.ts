import type {
  EditorRepository,
  LifecycleTransition,
} from "../contracts";

/*
 * The standalone app's own draft/publish pair: Publish only while a
 * draft, Revert to draft only once published.
 */
export const DEFAULT_LIFECYCLE_TRANSITIONS: LifecycleTransition[] = [
  {
    id: "publish",
    label: "Publish",
    targetIsDraft: false,
    tone: "success",
    isVisible: (context) => context.isDraft,
  },
  {
    id: "unpublish",
    label: "Revert to draft",
    targetIsDraft: true,
    tone: "warning",
    isVisible: (context) => !context.isDraft,
  },
];


/**
 * The transitions for a host and profile (see
 * EditorRepository.lifecycleTransitions). A host array replaces only
 * the default Publish/Revert pair: a host without drafts (`[]`) keeps
 * the profile's own steps such as Reject. The function form sees the
 * whole list and may change anything.
 */
export function resolveLifecycleTransitions(
  host: EditorRepository["lifecycleTransitions"],
  profileTransitions: LifecycleTransition[] = [],
): LifecycleTransition[] {
  if (typeof host === "function") {
    return host([...DEFAULT_LIFECYCLE_TRANSITIONS, ...profileTransitions]);
  }

  return [...(host ?? DEFAULT_LIFECYCLE_TRANSITIONS), ...profileTransitions];
}
