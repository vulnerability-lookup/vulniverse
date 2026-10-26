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

import {
  recordQualityPanel,
} from "./record-quality";

export const BUILTIN_PANELS:
  EditorPanel[] = [
    templatesPanel,
    recordStatsPanel,
    vulnerabilityLookupPanel,
    cveProgramPanel,
    recordQualityPanel,
  ];


export {
  templatesPanel,
};

export {
  recordStatsPanel,
};

export {
  recordQualityPanel,
};

export {
  cveProgramPanel,
  vulnerabilityLookupPanel,
};

export {
  gcveIdentifierPanel,
} from "./gcve-identifier";
