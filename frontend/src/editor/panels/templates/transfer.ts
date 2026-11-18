import type {
  Template,
  TemplateField,
} from "../../contracts";

/*
 * A template as a file, to share it or move it to another instance:
 * {format, version, profile, name, fields}. The profile goes along, as
 * a template only fits records of its profile.
 */

export const TEMPLATE_FILE_FORMAT = "vulniverse-template";

export interface TemplateFile {
  format: typeof TEMPLATE_FILE_FORMAT;
  version: 1;
  profile: string;
  name: string;
  fields: TemplateField[];
}

export function exportTemplate(template: Template): string {
  const file: TemplateFile = {
    format: TEMPLATE_FILE_FORMAT,
    version: 1,
    profile: template.profile,
    name: template.name,
    fields: template.fields,
  };

  return `${JSON.stringify(file, null, 2)}\n`;
}

/** A safe file name for the template. */
export function templateFileName(template: Template): string {
  return `${template.name.replace(/[^\w.-]+/g, "_") || "template"}.template.json`;
}

function isField(value: unknown): value is TemplateField {
  return typeof value === "object" && value !== null
    && typeof (value as TemplateField).path === "string"
    && (value as TemplateField).path.trim().length > 0
    && "value" in value;
}

/** The template in a file, for `profile`; throws with a message for the user. */
export function parseTemplateFile(
  text: string,
  profile: string,
): { name: string; fields: TemplateField[] } {
  let file: unknown;

  try {
    file = JSON.parse(text);
  } catch {
    throw new Error("That file isn't JSON.");
  }

  const candidate = file as Partial<TemplateFile> | null;

  if (candidate?.format !== TEMPLATE_FILE_FORMAT) {
    throw new Error("That file isn't an exported Vulniverse template.");
  }

  if (candidate.profile !== profile) {
    throw new Error(
      `This template is for ${String(candidate.profile)}, this record is ${profile};`
      + " import it from a record of that profile.",
    );
  }

  if (
    typeof candidate.name !== "string" || !candidate.name.trim()
    || !Array.isArray(candidate.fields) || !candidate.fields.every(isField)
  ) {
    throw new Error("The template in that file is incomplete.");
  }

  return { name: candidate.name.trim(), fields: candidate.fields };
}

/** `name`, or "name (2)", "name (3)", … if it's taken. */
export function freeName(name: string, taken: Set<string>): string {
  let candidate = name;

  for (let number = 2; taken.has(candidate.toLowerCase()); number += 1) {
    candidate = `${name} (${number})`;
  }

  return candidate;
}
