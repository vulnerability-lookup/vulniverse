import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { ref } from "vue";

import type { EditorContext, EditorRepository } from "../../../contracts";
import { editorRepositoryKey, editorStateKey } from "../../../core/context";
import { useEditorState } from "../../../core/state";
import Patch2VulnPanel from "../Patch2VulnPanel.vue";

const commit = (sha: string) => `https://github.com/acme/widget/commit/${sha}`;

function mountPanel() {
  const repository = { submitPatch2VulnJob: async () => ({}), getPatch2VulnJob: async () => ({}) };
  return mount(Patch2VulnPanel, {
    props: { context: { profile: "cve-5.2.0", record: {}, identifier: null } as unknown as EditorContext },
    global: {
      provide: {
        [editorRepositoryKey as symbol]: ref(repository as unknown as EditorRepository),
        [editorStateKey as symbol]: useEditorState(),
      },
    },
  });
}

describe("Patch2Vuln commit URLs", () => {
  it("names the lines the backend would refuse, and blocks Analyze until fixed", async () => {
    const panel = mountPanel();
    const urls = panel.find("textarea");
    const analyze = () => panel.find("button.btn-primary").element as HTMLButtonElement;

    await urls.setValue(`${commit("abcdef1")}\n\nhttps://gitlab.com/acme/widget/-/commit/abcdef1`);
    expect(panel.find("#patch2vuln-input-problem").text()).toBe("⚠ Line 3 is not a GitHub commit URL.");
    expect(analyze().disabled).toBe(true);

    await urls.setValue(`${commit("abcdef1")}\n${commit("1234567")}`);
    expect(panel.find("#patch2vuln-input-problem").exists()).toBe(false);
    expect(analyze().disabled).toBe(false);
  });

  it("counts the inputs against the limit", async () => {
    const panel = mountPanel();

    await panel.find("textarea").setValue(
      ["1111111", "2222222", "3333333", "4444444", "5555555", "6666666"].map(commit).join("\n"),
    );

    expect(panel.find("#patch2vuln-input-problem").text()).toBe("⚠ 6 patches; at most 5 per analysis.");
  });
});
