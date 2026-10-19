import type {
  EditorPanel,
} from "../contracts";

import {
  templatesPanel,
} from "./templates";

import {
  recordStatsPanel,
} from "./record-stats";

import {
  cveProgramPanel,
  vulnerabilityLookupPanel,
} from "./publication";


export const BUILTIN_PANELS:
  EditorPanel[] = [
    templatesPanel,
    recordStatsPanel,
    vulnerabilityLookupPanel,
    cveProgramPanel,
  ];


export {
  templatesPanel,
};

export {
  recordStatsPanel,
};

export {
  cveProgramPanel,
  vulnerabilityLookupPanel,
};

export {
  gcveIdentifierPanel,
} from "./gcve-identifier";
