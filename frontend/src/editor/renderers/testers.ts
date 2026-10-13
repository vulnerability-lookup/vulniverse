import {
  rankWith,
} from "@jsonforms/core";

import type {
  RankedTester,
  UISchemaElement,
} from "@jsonforms/core";


export function rendererOptionIs(
  name: string,
  rank = 10,
): RankedTester {
  return rankWith(
    rank,
    (
      uischema: UISchemaElement,
    ) => {
      const options = (
        uischema as {
          options?: {
            renderer?: string;
          };
        }
      ).options;

      return (
        options?.renderer
        === name
      );
    },
  );
}
