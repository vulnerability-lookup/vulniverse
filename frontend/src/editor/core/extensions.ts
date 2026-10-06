import {
  computed,
} from "vue";

import type {
  Component,
  Ref,
} from "vue";

import type {
  EditorModule,
  EditorModuleContext,
  EditorPanel,
} from "../contracts";

import type {
  EditorState,
} from "./state";

import {
  normalizeError,
} from "./errors";

import JsonSection from
  "../sections/JsonSection.vue";

import PreviewSection from
  "../sections/PreviewSection.vue";

import RejectedRecordSection from
  "../sections/RejectedRecordSection.vue";

import SchemaFormSection from
  "../sections/SchemaFormSection.vue";

interface EditorExtensionsOptions {
  state: EditorState;

  activeSection: Ref<string>;

  panels: Readonly<Ref<EditorPanel[]>>;
  modules: Readonly<Ref<EditorModule[]>>;

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
    preview: PreviewSection,
  };


export function useEditorExtensions(
  options: EditorExtensionsOptions,
) {
  const {
    state,
    activeSection,
    panels,
    modules,
    isRejected,
  } = options;

  const context =
    computed<EditorModuleContext>(() => ({
      identifier:
        state.identifier.value,

      profile:
        state.profile.value ??
        "cve-5.2.0",

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
    >(() => ({
      ...BUILTIN_SECTION_COMPONENTS,

      editor:
        isRejected.value
          ? RejectedRecordSection
          : SchemaFormSection,

      ...Object.fromEntries(
        visiblePanels.value.map(
          (panel) => [
            panel.id,
            panel.component,
          ],
        ),
      ),
    }));

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

  const visibleModules =
    computed(() =>
      modules.value
        .filter(
          (module) =>
            module.isVisible?.(
              context.value,
            ) ?? true,
        )
        .map(
          (module) => ({
            id: module.id,
            label: module.label,

            enabled:
              module.isEnabled?.(
                context.value,
              ) ?? true,
          }),
        ),
    );

  async function runModule(
    moduleId: string,
  ): Promise<void> {
    const module =
      modules.value.find(
        (candidate) =>
          candidate.id === moduleId,
      );

    if (
      !module ||
      !state.record.value
    ) {
      return;
    }

    state.saving.value = true;
    state.saveError.value = null;

    try {
      await module.run(
        context.value,
      );
    } catch (error) {
      const normalized =
        normalizeError(
          error,
          `Unable to run "${module.label}".`,
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

    visibleModules,

    runModule,
  };
}
