/*
 * Plain-language help for every metric the calculator offers: the
 * question the metric answers, what each value means, and for some a
 * tip about a common scoring mistake. Short paraphrases of the FIRST
 * CVSS specifications (linked in SPEC_URLS), not quotations.
 */

export interface MetricHelp {
  question: string;
  values: Record<string, string>;
  tip?: string;
}

type Version = "2.0" | "3.0" | "3.1" | "4.0";

export const SPEC_URLS: Record<Version, string> = {
  "2.0": "https://www.first.org/cvss/v2/guide",
  "3.0": "https://www.first.org/cvss/v3.0/specification-document",
  "3.1": "https://www.first.org/cvss/v3.1/specification-document",
  "4.0": "https://www.first.org/cvss/v4.0/specification-document",
};

const NOT_DEFINED = "Not Defined: no value given, the metric doesn't change the score.";

function impact(what: string, high: string, low: string): MetricHelp {
  return {
    question: `How badly is ${what} affected?`,
    values: {
      H: `High: ${high}`,
      L: `Low: ${low}`,
      N: "None: no impact.",
    },
  };
}

const CONFIDENTIALITY = [
  "the attacker can read everything, or gets critical data such as passwords or keys.",
  "some information is disclosed, but the attacker can't choose what, or only a little.",
] as const;

const INTEGRITY = [
  "the attacker can change any data, or data with serious consequences.",
  "the attacker can change some data, but can't choose what, or with little consequence.",
] as const;

const AVAILABILITY = [
  "the attacker can fully deny access, for as long as the attack lasts or permanently.",
  "performance is reduced or service is interrupted, but not fully denied.",
] as const;

const PRIVILEGES: MetricHelp = {
  question: "What access must the attacker already have before the attack?",
  values: {
    N: "None: no account or login needed.",
    L: "Low: a normal user account or basic rights.",
    H: "High: administrator rights or similar control.",
  },
  tip: "Count what the attacker needs before the attack. What they gain by it goes into the impact metrics.",
};

const V3: Record<string, MetricHelp> = {
  AV: {
    question: "How close to the vulnerable component must the attacker be?",
    values: {
      N: "Network: from anywhere on the network, including the internet.",
      A: "Adjacent: only from the same local network segment (same subnet, Bluetooth, Wi-Fi).",
      L: "Local: needs local access (console, SSH session), or a local user must open something.",
      P: "Physical: must touch or handle the device.",
    },
    tip: "A file sent over the network that a user must open is Local with User Interaction Required, not Network.",
  },
  AC: {
    question: "Must conditions outside the attacker's control be met?",
    values: {
      L: "Low: no special conditions, the attack works reliably every time.",
      H: "High: success depends on things like winning a race, a man-in-the-middle position, or target-specific secrets.",
    },
    tip: "This is not about how hard the exploit is to write.",
  },
  PR: PRIVILEGES,
  UI: {
    question: "Must a person other than the attacker do something?",
    values: {
      N: "None: no one else has to act.",
      R: "Required: a user must act, e.g. click a link, open a file or install something.",
    },
  },
  S: {
    question: "Can the impact reach beyond the vulnerable component's own security boundary?",
    values: {
      U: "Unchanged: the impact stays inside the same security authority (same application, same OS).",
      C: "Changed: it crosses a boundary, e.g. a sandbox or VM escape, or XSS from a web app into the user's browser.",
    },
    tip: "With Changed, rate the impact on whichever component is hurt most. It also changes the weight of Privileges Required.",
  },
  C: { ...impact("confidentiality", ...CONFIDENTIALITY), question: "How much information can the attacker read?" },
  I: { ...impact("integrity", ...INTEGRITY), question: "How much can the attacker change?" },
  A: { ...impact("availability", ...AVAILABILITY), question: "How much can the attacker disrupt the component?" },
};

const V4: Record<string, MetricHelp> = {
  AV: {
    ...V3.AV!,
    values: { ...V3.AV!.values, A: "Adjacent: only from a limited network, e.g. the same subnet, Bluetooth or a VPN shared with the target." },
  },
  AC: {
    question: "Must the attacker defeat a security measure or obtain a target-specific secret?",
    values: {
      L: "Low: nothing stands in the way that the attacker can't routinely get past.",
      H: "High: e.g. bypassing ASLR or DEP, or getting a secret key the target uses.",
    },
    tip: "Race conditions and man-in-the-middle positions moved to Attack Requirements in 4.0.",
  },
  AT: {
    question: "Does the attack depend on how the target is deployed or running?",
    values: {
      N: "None: works against any deployment.",
      P: "Present: needs a specific condition, e.g. winning a race, a man-in-the-middle position, or a certain configuration.",
    },
  },
  PR: PRIVILEGES,
  UI: {
    question: "Must a person other than the attacker do something?",
    values: {
      N: "None: no one else has to act.",
      P: "Passive: only limited, involuntary actions, e.g. visiting a page or viewing a message.",
      A: "Active: a deliberate action, e.g. importing a file, clicking through a warning, or installing something.",
    },
  },
  VC: impact("confidentiality of the vulnerable system itself", ...CONFIDENTIALITY),
  VI: impact("integrity of the vulnerable system itself", ...INTEGRITY),
  VA: impact("availability of the vulnerable system itself", ...AVAILABILITY),
  SC: {
    ...impact("confidentiality of other systems", ...CONFIDENTIALITY),
    tip: "Subsequent systems are everything beyond the vulnerable one, e.g. the user's browser after XSS. This replaces Scope from 3.x.",
  },
  SI: impact("integrity of other systems", ...INTEGRITY),
  SA: impact("availability of other systems", ...AVAILABILITY),

  E: {
    question: "Is the vulnerability being attacked?",
    values: {
      X: "Not Defined: assumes the worst case, Attacked.",
      A: "Attacked: attacks are reported, or exploit tools are publicly available.",
      P: "Proof-of-Concept: a proof-of-concept is public, but no attacks are known.",
      U: "Unreported: no public proof-of-concept and no reported attacks.",
    },
  },

  S: {
    question: "Can exploitation lead to physical harm to people?",
    values: {
      X: NOT_DEFINED,
      N: "Negligible: at most negligible consequences (IEC 61508).",
      P: "Present: marginal or worse consequences (IEC 61508).",
    },
  },
  AU: {
    question: "Could an attacker automate the attack across many targets?",
    values: {
      X: NOT_DEFINED,
      N: "No: at least one step from reconnaissance to exploitation can't be reliably automated.",
      Y: "Yes: every step can be automated.",
    },
  },
  R: {
    question: "How does the system recover after an attack?",
    values: {
      X: NOT_DEFINED,
      A: "Automatic: it recovers by itself.",
      U: "User: someone must step in manually.",
      I: "Irrecoverable: it can't be recovered by the user.",
    },
  },
  V: {
    question: "How much does one successful attack give the attacker?",
    values: {
      X: NOT_DEFINED,
      D: "Diffuse: little, e.g. a single user's email client.",
      C: "Concentrated: a lot, e.g. a central email server.",
    },
  },
  RE: {
    question: "How much effort does it take users to respond?",
    values: {
      X: NOT_DEFINED,
      L: "Low: e.g. a configuration change or a note in the documentation.",
      M: "Moderate: e.g. an update that needs some planning.",
      H: "High: e.g. firmware or hardware replacement, or long downtime.",
    },
  },
  U: {
    question: "How urgent does the vendor rate it?",
    values: {
      X: NOT_DEFINED,
      Clear: "Clear: informational, no urgency.",
      Green: "Green: reduced urgency.",
      Amber: "Amber: moderate urgency.",
      Red: "Red: highest urgency.",
    },
  },
};

for (const [key, kind] of [["CR", "confidentiality"], ["IR", "integrity"], ["AR", "availability"]] as const) {
  V4[key] = {
    question: `How important is the ${kind} of the affected system to your organisation?`,
    values: {
      X: "Not Defined: treated as High.",
      H: "High: losing it would have a catastrophic effect.",
      M: "Medium: losing it would have a serious effect.",
      L: "Low: losing it would have a limited effect.",
    },
  };
}

const V2: Record<string, MetricHelp> = {
  AV: {
    question: "From where can the attacker exploit it?",
    values: {
      L: "Local: needs physical or local shell access.",
      A: "Adjacent Network: only from the same local network segment.",
      N: "Network: remotely, from anywhere on the network.",
    },
  },
  AC: {
    question: "How complex is the attack once the attacker has access?",
    values: {
      H: "High: very specific conditions, e.g. winning a race or rare configurations.",
      M: "Medium: somewhat specialised conditions, e.g. a non-default configuration.",
      L: "Low: no special conditions.",
    },
  },
  Au: {
    question: "How often must the attacker log in before the attack?",
    values: {
      M: "Multiple: two or more times.",
      S: "Single: once.",
      N: "None: no login needed.",
    },
  },
  ...Object.fromEntries(
    [["C", "confidentiality"], ["I", "integrity"], ["A", "availability"]].map(([key, kind]) => [key, {
      question: `How badly is ${kind} affected?`,
      values: {
        N: "None: no impact.",
        P: "Partial: considerable, but limited impact.",
        C: "Complete: total compromise.",
      },
    }]),
  ),
};

/** Help for a metric of a CVSS version, or undefined when there's none. */
export function metricHelp(version: Version, key: string): MetricHelp | undefined {
  if (version === "2.0") return V2[key];
  if (version !== "4.0") return V3[key];

  // CVSS 4.0's Modified metrics (MAV, MVC, …) are their base metric
  // re-rated for your own environment.
  const base = key.startsWith("M") ? V4[key.slice(1)] : undefined;

  if (base && !V4[key]) {
    return {
      question: `In your environment: ${base.question.charAt(0).toLowerCase()}${base.question.slice(1)}`,
      values: {
        X: "Not Defined: uses the base metric's value.",
        S: "Safety: the impact can lead to physical harm (IEC 61508).",
        ...base.values,
      },
    };
  }

  return V4[key];
}
