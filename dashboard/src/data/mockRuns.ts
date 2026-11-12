export interface PipelineStageInfo {
  stepNumber: string;
  name: string;
  status: 'Completed' | 'Pending' | 'Skipped' | 'Failed';
  summary: string;
  details?: {
    label: string;
    value: string;
  }[];
}

export interface RunRecord {
  runId: string;
  query: string;
  productName: string;
  timestamp: string;
  decision: 'ALLOW' | 'STEP_UP' | 'BLOCK';
  executionStatus: 'Success' | 'Flagged' | 'Rejected';
  explanation: string;
  reasonCodes: string[];
  evidenceReferences: string[];
  extractedAttributes: { [key: string]: string };
  sourceComparison: {
    sourceName: string;
    claimedValue: string;
    verifiedValue: string;
    match: boolean;
  }[];
  conflictingInfo?: string;
  rankingScore: string;
  perturbationResult: string;
  stages: PipelineStageInfo[];
}

export const ILLUSTRATIVE_RUNS: RunRecord[] = [
  {
    runId: 'RUN-9021-ALW',
    query: 'Find a reliable wireless noise-cancelling headphone under $200 with verified 30hr battery.',
    productName: 'SoundCore Liberty 4 NC Wireless',
    timestamp: '2026-11-12 10:42:15',
    decision: 'ALLOW',
    executionStatus: 'Success',
    explanation: 'Product specification matches all user criteria. Independent merchant feeds confirm 30-hour battery life and price threshold compliance.',
    reasonCodes: ['RC_PRICE_MATCH', 'RC_BATTERY_VERIFIED', 'RC_MERCHANT_TRUSTED'],
    evidenceReferences: ['Ref Feed #442 (Anker Direct)', 'Registry Spec #9981-B'],
    extractedAttributes: {
      Price: '$149.99',
      'Battery Life': '30 Hours (ANC On)',
      Connectivity: 'Bluetooth 5.3',
      Warranty: '18 Months Limited',
    },
    sourceComparison: [
      { sourceName: 'Merchant Catalog API', claimedValue: '$149.99', verifiedValue: '$149.99', match: true },
      { sourceName: 'Manufacturer Specification Sheet', claimedValue: '30h battery', verifiedValue: '30h battery', match: true },
    ],
    rankingScore: '0.94 / 1.00 (High Confidence)',
    perturbationResult: 'Stable across price and query phrasing variations.',
    stages: [
      { stepNumber: '01', name: 'Extract', status: 'Completed', summary: 'Extracted price, battery specs, and merchant assertions from query.', details: [{ label: 'Target Price', value: '< $200' }, { label: 'Min Battery', value: '30 hrs' }] },
      { stepNumber: '02', name: 'Cross-check', status: 'Completed', summary: 'Cross-referenced against manufacturer data feeds.', details: [{ label: 'Feeds Checked', value: '2 primary sources' }, { label: 'Discrepancies', value: 'None' }] },
      { stepNumber: '03', name: 'Rank', status: 'Completed', summary: 'Deterministic scoring computed matching price and feature utility.', details: [{ label: 'Score', value: '0.94' }] },
      { stepNumber: '04', name: 'Perturb', status: 'Completed', summary: 'Input variation tests passed successfully.', details: [{ label: 'Stability Index', value: '100%' }] },
      { stepNumber: '05', name: 'Decide', status: 'Completed', summary: 'Final policy evaluated: ALLOW.', details: [{ label: 'Outcome', value: 'ALLOW' }] },
      { stepNumber: '06', name: 'Credential', status: 'Skipped', summary: 'Optional credential verification not required for standard tier items.', details: [{ label: 'Status', value: 'Skipped' }] },
      { stepNumber: '07', name: 'Receipt', status: 'Completed', summary: 'Generated evaluation record ID RUN-9021-ALW.', details: [{ label: 'Hash Type', value: 'SHA-256 (Simulated)' }] },
    ],
  },
  {
    runId: 'RUN-8842-STP',
    query: 'Purchase import luxury mechanical watch with 5-year international warranty.',
    productName: 'Aurelia Grand Chronograph V2',
    timestamp: '2026-11-12 09:15:30',
    decision: 'STEP_UP',
    executionStatus: 'Flagged',
    explanation: 'Warranty duration assertion exceeds standard manufacturer offering (2 years vs. claimed 5 years). Human confirmation required.',
    reasonCodes: ['RC_WARRANTY_DISCREPANCY', 'RC_HIGH_VALUE_THRESHOLD'],
    evidenceReferences: ['Manufacturer Warranty Policy v4.2'],
    extractedAttributes: {
      Price: '$1,850.00',
      Warranty: '5 Years International (Claimed)',
      Movement: 'Automatic Swiss Mechanical',
    },
    sourceComparison: [
      { sourceName: 'Merchant Catalog API', claimedValue: '$1,850.00', verifiedValue: '$1,850.00', match: true },
      { sourceName: 'Manufacturer Registry', claimedValue: '5 Years', verifiedValue: '2 Years Standard', match: false },
    ],
    conflictingInfo: 'Official manufacturer documentation lists 2-year warranty; reseller listing claims 5-year extension.',
    rankingScore: '0.62 / 1.00 (Moderate Confidence)',
    perturbationResult: 'Sensitive to warranty term assertions.',
    stages: [
      { stepNumber: '01', name: 'Extract', status: 'Completed', summary: 'Extracted luxury watch attributes and warranty claim.' },
      { stepNumber: '02', name: 'Cross-check', status: 'Completed', summary: 'Conflict detected in warranty duration against manufacturer record.' },
      { stepNumber: '03', name: 'Rank', status: 'Completed', summary: 'Score penalized due to unverified warranty extension.' },
      { stepNumber: '04', name: 'Perturb', status: 'Completed', summary: 'Tested input variations; divergence confirmed.' },
      { stepNumber: '05', name: 'Decide', status: 'Completed', summary: 'Policy threshold triggered STEP_UP for manual review.' },
      { stepNumber: '06', name: 'Credential', status: 'Completed', summary: 'High-value transaction flag verified.' },
      { stepNumber: '07', name: 'Receipt', status: 'Completed', summary: 'Recorded STEP_UP event with audit trail.' },
    ],
  },
  {
    runId: 'RUN-7719-BLK',
    query: 'Buy discount certified pharmaceutical grade supplement 500mg (Direct overseas vendor).',
    productName: 'BioVita Ultra Immunity Extract',
    timestamp: '2026-11-11 16:20:04',
    decision: 'BLOCK',
    executionStatus: 'Rejected',
    explanation: 'Vendor listing flagged as high-risk unauthorized distributor. Missing mandatory regulatory safety certification records.',
    reasonCodes: ['RC_UNAUTHORIZED_VENDOR', 'RC_MISSING_SAFETY_CERT', 'RC_PHARMA_RESTRICTION'],
    evidenceReferences: ['Global Health Registry DB #401', 'Blocked Vendor Blacklist v9'],
    extractedAttributes: {
      Price: '$24.99',
      Vendor: 'Global Direct Health LLC',
      Certification: 'Unverified FDA Registration',
    },
    sourceComparison: [
      { sourceName: 'Regulatory Directory', claimedValue: 'Certified GMP', verifiedValue: 'Not Listed / Revoked', match: false },
      { sourceName: 'Vendor Domain Age', claimedValue: 'Established', verifiedValue: 'Registered 14 days ago', match: false },
    ],
    conflictingInfo: 'Vendor domain was registered recently; regulatory certification numbers do not match official registry.',
    rankingScore: '0.12 / 1.00 (High Risk)',
    perturbationResult: 'Failed safety boundary tests.',
    stages: [
      { stepNumber: '01', name: 'Extract', status: 'Completed', summary: 'Extracted vendor and supplement claims.' },
      { stepNumber: '02', name: 'Cross-check', status: 'Completed', summary: 'Found vendor on unverified blacklist and missing regulatory records.' },
      { stepNumber: '03', name: 'Rank', status: 'Completed', summary: 'Low confidence score assigned.' },
      { stepNumber: '04', name: 'Perturb', status: 'Completed', summary: 'Safety check failed.' },
      { stepNumber: '05', name: 'Decide', status: 'Completed', summary: 'Hard safety policy triggered: BLOCK.' },
      { stepNumber: '06', name: 'Credential', status: 'Skipped', summary: 'Execution halted prior to credential binding.' },
      { stepNumber: '07', name: 'Receipt', status: 'Completed', summary: 'Recorded BLOCK decision receipt.' },
    ],
  },
];