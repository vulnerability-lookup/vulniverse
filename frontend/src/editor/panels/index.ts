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

import {
  patch2vulnPanel,
} from "./patch2vuln";

export const BUILTIN_PANELS:
  EditorPanel[] = [
    templatesPanel,
    recordStatsPanel,
    vulnerabilityLookupPanel,
    cveProgramPanel,
    recordQualityPanel,
    patch2vulnPanel,
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
  patch2vulnPanel,
};

export {
  gcveIdentifierPanel,
} from "./gcve-identifier";
