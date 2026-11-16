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

import {
  vulnerabilityRecordsPanel,
} from "./vulnerability-records";

export const BUILTIN_PANELS:
  EditorPanel[] = [
    templatesPanel,
    recordStatsPanel,
    vulnerabilityLookupPanel,
    cveProgramPanel,
    recordQualityPanel,
    patch2vulnPanel,
    vulnerabilityRecordsPanel,
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
  vulnerabilityRecordsPanel,
};
