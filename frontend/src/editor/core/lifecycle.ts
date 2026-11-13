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
 * EditorRepository.lifecycleTransitions). The profile's own steps come
 * after the default Publish/Revert pair, or instead of it when the
 * profile says so (replacesDefaults: e.g. CSAF's Release and Update).
 * A host array replaces only that default pair: a host without drafts
 * (`[]`) keeps the profile's own steps such as Reject. The function
 * form sees the whole list and may change anything.
 */
export function resolveLifecycleTransitions(
  host: EditorRepository["lifecycleTransitions"],
  profileTransitions: LifecycleTransition[] = [],
  replacesDefaults = false,
): LifecycleTransition[] {
  const defaults = replacesDefaults ? [] : DEFAULT_LIFECYCLE_TRANSITIONS;

  if (typeof host === "function") {
    return host([...defaults, ...profileTransitions]);
  }

  return [...(host ?? defaults), ...profileTransitions];
}
