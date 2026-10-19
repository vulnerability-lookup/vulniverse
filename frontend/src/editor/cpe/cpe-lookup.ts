/*
 * Copied verbatim from the bundled CVE schema's
 * #/definitions/cpe22and23 (CVE_Record_Format_bundled.json) -- every
 * "CPE Name" item (e.g. affected[].cpes) resolves this exact $ref,
 * so an exact string match reliably identifies that field shape,
 * the same technique reference-lookup.ts uses for CWE_ID_PATTERN/
 * CAPEC_ID_PATTERN.
 */
export const CPE_NAME_PATTERN =
  "([c][pP][eE]:/[AHOaho]?(:[A-Za-z0-9._\\-~%]*){0,6})|(cpe:2\\.3:[aho*\\-](:(((\\?*|\\*?)([a-zA-Z0-9\\-._]|(\\\\[\\\\*?!\"#$%&'()+,/:;<=>@\\[\\]\\^`{|}~]))+(\\?*|\\*?))|[*\\-])){5}(:(([a-zA-Z]{2,3}(-([a-zA-Z]{2}|[0-9]{3}))?)|[*\\-]))(:(((\\?*|\\*?)([a-zA-Z0-9\\-._]|(\\\\[\\\\*?!\"#$%&'()+,/:;<=>@\\[\\]\\^`{|}~]))+(\\?*|\\*?))|[*\\-])){4})";

export function isCpeNamePattern(
  pattern: unknown,
): boolean {
  return pattern === CPE_NAME_PATTERN;
}
