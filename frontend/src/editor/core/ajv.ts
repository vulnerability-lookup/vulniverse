import {
  createAjv,
} from "@jsonforms/core";


export const editorAjv =
  createAjv();


editorAjv.addFormat(
  "long-text",
  {
    type: "string",
    validate: () => true,
  },
);
