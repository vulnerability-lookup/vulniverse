import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { ref } from "vue";

import type { EditorContext, EditorRepository } from "../../../contracts";
import { editorRepositoryKey, editorStateKey } from "../../../core/context";
import { useEditorState } from "../../../core/state";
import Patch2VulnPanel from "../Patch2VulnPanel.vue";

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

describe("Patch2Vuln vendor and product", () => {
  it("follow the commit URL until the user types their own", async () => {
    const panel = mountPanel();
    const [vendor, product] = panel.findAll<HTMLInputElement>("input:not([type=file])");
    const urls = panel.find("textarea");

    await urls.setValue("https://github.com/apache/httpd/commit/abc");
    expect([vendor!.element.value, product!.element.value]).toEqual(["apache", "httpd"]);
    expect(panel.find("#patch2vuln-autofilled").exists()).toBe(true);

    await vendor!.setValue("Apache Software Foundation");
    await urls.setValue("https://github.com/nginx/nginx/commit/abc");
    expect([vendor!.element.value, product!.element.value]).toEqual(["Apache Software Foundation", "nginx"]);

    await product!.setValue("NGINX");
    expect(panel.find("#patch2vuln-autofilled").exists()).toBe(false);
  });
});
