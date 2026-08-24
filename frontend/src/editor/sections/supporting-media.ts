/*
 * Turns a raw supportingMedia item ({type, value, base64?}) into a
 * safe-to-render description for PreviewSection, via
 * SupportingMediaPreview.vue.
 *
 * This content is CNA/ADP-submitted and often third-party — markdown
 * and HTML are run through DOMPurify before ever reaching v-html, and
 * tags capable of loading further active content (iframe/object/
 * embed) or carrying attacker-controlled CSS (style, style=) are
 * explicitly forbidden on top of DOMPurify's own defaults. Media types this
 * doesn't recognize deliberately fall back to a plain "not shown"
 * note rather than guessing how to render them.
 */

import DOMPurify from "dompurify";
import { marked } from "marked";

export interface SupportingMediaItem {
  type?: string;
  value?: string;
  base64?: boolean;
}

export type DescribedMedia =
  | { kind: "html"; type: string; html: string }
  | { kind: "text"; type: string; text: string }
  | { kind: "image"; type: string; src: string }
  | { kind: "audio"; type: string; src: string }
  | { kind: "unsupported"; type: string; reason: string };

function sanitize(
  html: string,
): string {
  return DOMPurify.sanitize(html, {
    FORBID_TAGS: ["iframe", "object", "embed", "style", "link", "meta", "base", "form"],
    FORBID_ATTR: ["style"],
  });
}

/*
 * atob() alone mangles any character outside the Latin-1 range —
 * decoding the raw bytes and running them through TextDecoder is
 * what actually reproduces the original UTF-8 text.
 */
function decodeBase64Utf8(
  base64: string,
): string {
  try {
    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));

    return new TextDecoder("utf-8").decode(bytes);
  } catch {
    return base64;
  }
}

function decodeTextValue(
  value: string,
  base64: boolean | undefined,
): string {
  return base64 ? decodeBase64Utf8(value) : value;
}

export function describeMedia(
  media: SupportingMediaItem,
): DescribedMedia {
  const type = (media.type ?? "").toLowerCase().trim();
  const rawValue = media.value ?? "";

  if (type.startsWith("image/")) {
    if (!media.base64) {
      return {
        kind: "unsupported",
        type,
        reason: "Image media must be base64-encoded to preview.",
      };
    }

    return {
      kind: "image",
      type,
      src: `data:${type};base64,${rawValue}`,
    };
  }

  if (type.startsWith("audio/")) {
    if (!media.base64) {
      return {
        kind: "unsupported",
        type,
        reason: "Audio media must be base64-encoded to preview.",
      };
    }

    return {
      kind: "audio",
      type,
      src: `data:${type};base64,${rawValue}`,
    };
  }

  if (type === "text/markdown") {
    const text = decodeTextValue(rawValue, media.base64);
    const rawHtml = marked.parse(text, { async: false }) as string;

    return {
      kind: "html",
      type,
      html: sanitize(rawHtml),
    };
  }

  if (type === "text/html") {
    const text = decodeTextValue(rawValue, media.base64);

    return {
      kind: "html",
      type,
      html: sanitize(text),
    };
  }

  if (type === "text/plain" || type === "") {
    return {
      kind: "text",
      type,
      text: decodeTextValue(rawValue, media.base64),
    };
  }

  return {
    kind: "unsupported",
    type,
    reason: `Preview doesn't support "${type}" media yet.`,
  };
}
