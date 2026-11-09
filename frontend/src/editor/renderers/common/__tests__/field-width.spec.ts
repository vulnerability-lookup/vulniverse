import { describe, expect, it } from "vitest";

import { fieldWidth } from "../field-width";

describe("fieldWidth", () => {
  it("makes IDs, enums, dates and numbers short", () => {
    expect(fieldWidth({ type: "string", pattern: "^CVE-[0-9]{4}-[0-9]{4,19}$" })).toBe("short");
    expect(fieldWidth({ type: "string", enum: ["PUBLISHED", "REJECTED"] })).toBe("short");
    expect(fieldWidth({ type: "string", format: "date-time" })).toBe("short");
    expect(fieldWidth({ type: "string", maxLength: 32 })).toBe("short");
    expect(fieldWidth({ type: "integer" })).toBe("short");
    expect(fieldWidth({ type: "boolean" })).toBe("short");
  });

  it("makes plain strings and URLs medium", () => {
    expect(fieldWidth({ type: "string", maxLength: 256 })).toBe("medium");
    expect(fieldWidth({ type: "string", format: "uri" })).toBe("medium");
    expect(fieldWidth({ type: "string" })).toBe("medium");
    expect(fieldWidth({ type: "string", format: "uuid" })).toBe("medium");
    expect(fieldWidth({
      type: "string",
      pattern: "^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-4[0-9A-Fa-f]{3}-[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}$",
    })).toBe("medium");
  });

  it("makes structured, long and custom-rendered fields full width", () => {
    expect(fieldWidth({ type: "object", properties: {} })).toBe("full");
    expect(fieldWidth({ type: ["array", "null"] })).toBe("full");
    expect(fieldWidth({ type: "string", maxLength: 4096 })).toBe("full");
    expect(fieldWidth({ oneOf: [{ type: "string" }, { type: "number" }] })).toBe("full");
    expect(fieldWidth({ type: "string" }, { multi: true })).toBe("full");
    expect(fieldWidth({ type: "string", pattern: "x" }, { renderer: "vulniverse-tags" })).toBe("full");
    expect(fieldWidth(undefined)).toBe("full");
  });

  it("lets the layout file override the guess", () => {
    expect(fieldWidth({ type: "object" }, { width: "short" })).toBe("short");
    expect(fieldWidth({ type: "integer" }, { width: "full" })).toBe("full");
    expect(fieldWidth({ type: "integer" }, { width: "huge" })).toBe("short");
  });
});
