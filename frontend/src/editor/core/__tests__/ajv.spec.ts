import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { EDITOR_PROFILES } from "../../profiles";
import { ajvForSchema, editorAjv, editorAjv2020 } from "../ajv";

// The official CSAF 2.1 example the backend tests use too.
const csafExample = JSON.parse(readFileSync(
  // Tests run from frontend/.
  resolve("../backend/tests/fixtures/csaf/bsi-2022-0001.json"),
  "utf-8",
)) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any -- test fixture

function csafValidator() {
  const profile = EDITOR_PROFILES.find((candidate) => candidate.id === "csaf-2.1")!;

  return ajvForSchema(profile.schema).compile(profile.schema);
}

describe("ajvForSchema", () => {
  it("compiles every profile's authoring schema with its dialect's validator", () => {
    for (const profile of EDITOR_PROFILES) {
      const ajv = ajvForSchema(profile.schema);

      expect(ajv).toBe(profile.id === "csaf-2.1" ? editorAjv2020 : editorAjv);
      expect(() => ajv.compile(profile.schema)).not.toThrow();
    }
  });

  it("accepts the official CSAF example", () => {
    const validate = csafValidator();

    validate(csafExample);

    // The errors, rather than a bare false, make a failure readable.
    expect(validate.errors).toBeNull();
  });

  it("checks CSAF's 2020-12 dependentRequired rule", () => {
    const validate = csafValidator();
    const document = structuredClone(csafExample);

    // A contact with an OpenPGP key URL needs an email.
    document.document.publisher.contact = {
      public_openpgp_key_url: "https://example.com/key.asc",
    };

    expect(validate(document)).toBe(false);
    // Reported as "dependencies", so JSON Forms shows it on the email field.
    expect(validate.errors).toContainEqual(expect.objectContaining({
      keyword: "dependencies",
      instancePath: "/document/publisher/contact",
      params: expect.objectContaining({ missingProperty: "email" }),
    }));
  });
});

describe("multipleOf", () => {
  it("accepts every CVSS score despite floating-point division", () => {
    // FIRST's CVSS 4.0 schema: baseScore multipleOf 0.1; 5.3 / 0.1 is 52.999… in JS.
    for (const ajv of [editorAjv, editorAjv2020]) {
      const validate = ajv.compile({ type: "number", multipleOf: 0.1 });
      const rejected = Array.from({ length: 101 }, (_, i) => i / 10).filter((score) => !validate(score));

      expect(rejected).toEqual([]);
      expect(validate(5.35)).toBe(false);
    }
  });
});
