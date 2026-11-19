import { describe, expect, it } from "vitest";

import { exportTemplate, freeName, parseTemplateFile, templateFileName } from "../transfer";

const template = {
  id: "1",
  profile: "cve-5.2.0",
  name: "Acme Widget",
  fields: [{ path: "containers.cna.affected.0.vendor", value: "Acme" }],
};

describe("template files", () => {
  it("round-trips name and fields, without the id", () => {
    const text = exportTemplate(template);

    expect(JSON.parse(text)).not.toHaveProperty("id");
    expect(parseTemplateFile(text, "cve-5.2.0")).toEqual({
      name: "Acme Widget",
      fields: template.fields,
    });
    expect(templateFileName(template)).toBe("Acme_Widget.template.json");
  });

  it("refuses other files, profiles and incomplete templates", () => {
    expect(() => parseTemplateFile("not json", "cve-5.2.0")).toThrow("isn't JSON");
    expect(() => parseTemplateFile("{}", "cve-5.2.0")).toThrow("isn't an exported Vulniverse template");
    expect(() => parseTemplateFile(exportTemplate({ ...template, profile: "osv-1.9.2" }), "cve-5.2.0"))
      .toThrow("This template is for osv-1.9.2");

    const incomplete = exportTemplate({ ...template, fields: [{ path: "a" } as never] });
    expect(() => parseTemplateFile(incomplete, "cve-5.2.0")).toThrow("incomplete");
  });

  it("numbers a taken name", () => {
    expect(freeName("Acme", new Set())).toBe("Acme");
    expect(freeName("Acme", new Set(["acme", "acme (2)"]))).toBe("Acme (3)");
  });
});
