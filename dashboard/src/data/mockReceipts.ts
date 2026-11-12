export interface ReceiptRecord {
  receiptId: string;
  runId: string;
  timestamp: string;
  decision: 'ALLOW' | 'STEP_UP' | 'BLOCK';
  verificationStatus: 'Verified (Illustrative)' | 'Pending' | 'Flagged';
  payloadHash: string;
  previousReceiptHash: string;
  signature: string;
  publicKey: string;
  algorithm: string;
  reasonCodes: string[];
  evidenceReferences: string[];
  productName: string;
  query: string;
}

export const ILLUSTRATIVE_RECEIPTS: ReceiptRecord[] = [
  {
    receiptId: 'RCPT-9021-ALW',
    runId: 'RUN-9021-ALW',
    timestamp: '2026-11-12 10:42:16',
    decision: 'ALLOW',
    verificationStatus: 'Verified (Illustrative)',
    payloadHash: '0x4f89c3a2e1d7b6f5091827364556a7b8c9d0e1f2',
    previousReceiptHash: '0x8831a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9',
    signature: 'sig_ed25519_9981a27364f509182734556a7b8c9d0e1',
    publicKey: 'pub_key_trussted_validator_v2_99',
    algorithm: 'Ed25519 (Mock Demonstration)',
    reasonCodes: ['RC_PRICE_MATCH', 'RC_BATTERY_VERIFIED', 'RC_MERCHANT_TRUSTED'],
    evidenceReferences: ['Ref Feed #442 (Anker Direct)', 'Registry Spec #9981-B'],
    productName: 'SoundCore Liberty 4 NC Wireless',
    query: 'Find a reliable wireless noise-cancelling headphone under $200 with verified 30hr battery.',
  },
  {
    receiptId: 'RCPT-8842-STP',
    runId: 'RUN-8842-STP',
    timestamp: '2026-11-12 09:15:31',
    decision: 'STEP_UP',
    verificationStatus: 'Verified (Illustrative)',
    payloadHash: '0x3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b',
    previousReceiptHash: '0x4f89c3a2e1d7b6f5091827364556a7b8c9d0e1f2',
    signature: 'sig_ed25519_8842b1c0d9e8f7a6b5c4d3e2f1a0b9c8d',
    publicKey: 'pub_key_trussted_validator_v2_99',
    algorithm: 'Ed25519 (Mock Demonstration)',
    reasonCodes: ['RC_WARRANTY_DISCREPANCY', 'RC_HIGH_VALUE_THRESHOLD'],
    evidenceReferences: ['Manufacturer Warranty Policy v4.2'],
    productName: 'Aurelia Grand Chronograph V2',
    query: 'Purchase import luxury mechanical watch with 5-year international warranty.',
  },
  {
    receiptId: 'RCPT-7719-BLK',
    runId: 'RUN-7719-BLK',
    timestamp: '2026-11-11 16:20:05',
    decision: 'BLOCK',
    verificationStatus: 'Verified (Illustrative)',
    payloadHash: '0x11223344556677889900aabbccddeeff11223344',
    previousReceiptHash: '0x3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b',
    signature: 'sig_ed25519_7719a27364f509182734556a7b8c9d0e1',
    publicKey: 'pub_key_trussted_validator_v2_99',
    algorithm: 'Ed25519 (Mock Demonstration)',
    reasonCodes: ['RC_UNAUTHORIZED_VENDOR', 'RC_MISSING_SAFETY_CERT', 'RC_PHARMA_RESTRICTION'],
    evidenceReferences: ['Global Health Registry DB #401', 'Blocked Vendor Blacklist v9'],
    productName: 'BioVita Ultra Immunity Extract',
    query: 'Buy discount certified pharmaceutical grade supplement 500mg (Direct overseas vendor).',
  },
];