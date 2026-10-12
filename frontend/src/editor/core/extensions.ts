import {
  computed,
} from "vue";

import type {
  Component,
  Ref,
} from "vue";

import type {
  EditorAction,
  EditorContext,
  EditorPanel,
} from "../contracts";

import type {
  EditorState,
} from "./state";

import {
  normalizeError,
} from "./errors";

import {
  GenericPreviewSection,
  JsonSection,
  SchemaFormSection,
} from "../sections";

import {
  DEFAULT_PROFILE_ID,
  getEditorProfile,
} from "../profiles";

interface EditorExtensionsOptions {
  state: EditorState;

  activeSection: Ref<string>;

  panels: Readonly<Ref<EditorPanel[]>>;
  actions: Readonly<Ref<EditorAction[]>>;

  isRejected: Readonly<Ref<boolean>>;

  onError(error: Error): void;
}

export const BUILTIN_NAVIGATION_ITEMS = [
  {
    id: "editor",
    label: "Editor",
  },
  {
    id: "preview",
    label: "Preview",
  },
  {
    id: "json",
    label: "Advanced JSON",
  },
];


const BUILTIN_SECTION_COMPONENTS:
  Record<string, Component> = {
    json: JsonSection,
    editor: SchemaFormSection,
  };


export function useEditorExtensions(
  options: EditorExtensionsOptions,
) {
  const {
    state,
    activeSection,
    panels,
    actions,
    isRejected,
  } = options;

  const activeProfile =
    computed(() =>
      getEditorProfile(
        state.profile.value ?? DEFAULT_PROFILE_ID,
      ),
    );

  const context =
    computed<EditorContext>(() => ({
      identifier:
        state.identifier.value,

      profile:
        state.profile.value ??
        DEFAULT_PROFILE_ID,

      record:
        state.record.value ??
        {},

      isDraft:
        state.isDraft.value,
    }));

  const visiblePanels =
    computed(() =>
      panels.value.filter(
        (panel) =>
          panel.isVisible?.(
            context.value,
          ) ?? true,
      ),
    );

  const panelNavigationItems =
    computed(() =>
      visiblePanels.value.map(
        (panel) => ({
          id: panel.id,
          label: panel.label,
        }),
      ),
    );

    const sectionComponents =
    computed<
      Record<string, Component>
    >(() => {
      const profile = activeProfile.value;

      const editorComponent =
        isRejected.value && profile.rejection?.editorComponent
          ? profile.rejection.editorComponent
          : SchemaFormSection;

      const previewComponent =
        profile.previewComponent ?? GenericPreviewSection;

      return {
        ...BUILTIN_SECTION_COMPONENTS,

        editor: editorComponent,
        preview: previewComponent,

        ...Object.fromEntries(
          visiblePanels.value.map(
            (panel) => [
              panel.id,
              panel.component,
            ],
          ),
        ),
      };
    });

  const currentSection =
    computed(() =>
      sectionComponents.value[
        activeSection.value
      ] ??
      SchemaFormSection,
    );

  const sectionProps =
    computed(() => {
      const isPanel =
        visiblePanels.value.some(
          (panel) =>
            panel.id ===
            activeSection.value,
        );

      return isPanel
        ? {
            context:
              context.value,
          }
        : {};
    });

  const visibleActions =
    computed(() =>
      actions.value
        .filter(
          (action) =>
            action.isVisible?.(
              context.value,
            ) ?? true,
        )
        .map(
          (action) => ({
            id: action.id,
            label: action.label,

            enabled:
              action.isEnabled?.(
                context.value,
              ) ?? true,
          }),
        ),
    );

  async function runAction(
    actionId: string,
  ): Promise<void> {
    const action =
      actions.value.find(
        (candidate) =>
          candidate.id === actionId,
      );

    if (
      !action ||
      !state.record.value
    ) {
      return;
    }

    state.saving.value = true;
    state.saveError.value = null;

    try {
      await action.run(
        context.value,
      );
    } catch (error) {
      const normalized =
        normalizeError(
          error,
          `Unable to run "${action.label}".`,
        );

      state.saveError.value =
        normalized;

      options.onError(
        normalized,
      );
    } finally {
      state.saving.value = false;
    }
  }

  return {
    context,

    visiblePanels,
    panelNavigationItems,

    currentSection,
    sectionProps,

    visibleActions,

    runAction,
  };
}
