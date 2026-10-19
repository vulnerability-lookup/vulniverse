import type {
  AnyRecord,
} from "./types";


export function providerLabel(
  container: AnyRecord,
): string {
  const providerMetadata =
    container.providerMetadata as
      | AnyRecord
      | undefined;

  return (
    (
      providerMetadata?.shortName as
        | string
        | undefined
    )
    ?? (
      providerMetadata?.orgId as
        | string
        | undefined
    )
    ?? "Unknown provider"
  );
}
