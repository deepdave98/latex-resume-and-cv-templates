import { zipSync } from 'fflate';

const encoder = new TextEncoder();
export const MAX_RECEIPT_BYTES = 64 * 1024;

export class SubmissionArchiveError extends Error {}

async function sha256(bytes) {
  if (typeof globalThis.crypto?.subtle?.digest !== 'function') {
    throw new SubmissionArchiveError('SHA-256 is unavailable. Open the downloaded reviewer in a current browser.');
  }
  let digest;
  try {
    digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  } catch {
    throw new Error('Could not calculate the PDF hash. Try again in a current browser.');
  }
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

function receiptValues(receipt) {
  if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)
      || Object.values(receipt).some(value => value !== null && typeof value === 'object')) {
    throw new SubmissionArchiveError('This is not a saved-copy receipt. Choose receipt.json from the archive.');
  }
  const { pdf, bytes, sha256: hash } = receipt;
  if (!Number.isSafeInteger(bytes) || bytes <= 0) {
    throw new SubmissionArchiveError('The receipt needs a positive whole-number byte count.');
  }
  if (typeof hash !== 'string' || !/^[0-9a-f]{64}$/iu.test(hash)) {
    throw new SubmissionArchiveError('The receipt needs a 64-character SHA-256 hash.');
  }
  const reserved = typeof pdf === 'string'
    && /^(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$/iu.test(pdf.split('.')[0].trimEnd());
  if (typeof pdf !== 'string' || !/\.pdf$/iu.test(pdf) || !/[^.]/u.test(pdf.slice(0, -4))
      || /[/\\:*?"<>|]/u.test(pdf) || /[\p{C}\p{Z}]/u.test(pdf.replaceAll(' ', '')) || reserved) {
    throw new SubmissionArchiveError('The receipt must name one local PDF file, without a path.');
  }
  return Object.freeze({ pdf, bytes, sha256: hash.toLowerCase() });
}

/** Read only the fields needed to compare bytes; a receipt does not authenticate its label or date. */
export function readSubmissionReceipt(text) {
  if (typeof text !== 'string') throw new SubmissionArchiveError('Choose a readable receipt.json file.');
  if (text.length > MAX_RECEIPT_BYTES || encoder.encode(text).length > MAX_RECEIPT_BYTES) {
    throw new SubmissionArchiveError('The receipt is too large. Choose a receipt.json no larger than 64 KiB.');
  }
  let receipt;
  try {
    receipt = JSON.parse(text);
  } catch {
    throw new SubmissionArchiveError('The receipt is not readable JSON. Choose receipt.json from a saved copy.');
  }
  const values = receiptValues(receipt);
  const keys = new Set();
  // JSON.parse has checked the syntax. Consume complete strings so quotes and
  // colons inside a label cannot be mistaken for duplicate property names.
  for (const token of text.matchAll(/("(?:\\.|[^"\\])*")(\s*:)?/gu)) {
    if (!token[2]) continue;
    const key = JSON.parse(token[1]);
    if (keys.has(key)) throw new SubmissionArchiveError('The receipt contains duplicate fields.');
    keys.add(key);
    if (key === 'bytes' && !/^\s*[1-9]\d*\s*[,}]/u.test(text.slice(token.index + token[0].length))) {
      throw new SubmissionArchiveError('The receipt needs a positive whole-number byte count.');
    }
  }
  return values;
}

/** Compare original bytes, including metadata and encryption; filenames may have changed. */
export async function verifySubmissionPDF(pdfBytes, receipt) {
  const expected = receiptValues(receipt);
  if (!(pdfBytes instanceof Uint8Array) || !pdfBytes.length) {
    throw new SubmissionArchiveError('Open the saved PDF before checking its receipt.');
  }
  if (pdfBytes.length !== expected.bytes) return { status: 'size-mismatch' };
  const pdf = new Uint8Array(pdfBytes);
  const hash = await sha256(pdf);
  return { status: hash === expected.sha256 ? 'match' : 'hash-mismatch' };
}

function labelSlug(label) {
  if (typeof label !== 'string' || !label.trim() || /[\p{C}\p{Z}]/u.test(label.replaceAll(' ', ''))) {
    throw new SubmissionArchiveError('Use a company/role label without line breaks or control characters.');
  }
  const characters = Array.from(label.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/gu, '')).slice(0, 80);
  while (encoder.encode(characters.join('')).length > 200) characters.pop();
  const slug = characters.join('').replace(/-+$/u, '');
  if (!slug) throw new SubmissionArchiveError('Include a letter or number in the company/role label.');
  return slug;
}

function localTimestamp(date) {
  if (!(date instanceof Date) || !Number.isFinite(date.getTime()) || date.getFullYear() < 1 || date.getFullYear() > 9999) {
    throw new SubmissionArchiveError('The save date is invalid. Check your device clock.');
  }
  const two = value => String(value).padStart(2, '0');
  const offset = date.getTimezoneOffset();
  const zone = `${offset > 0 ? '-' : '+'}${two(Math.floor(Math.abs(offset) / 60))}:${two(Math.abs(offset) % 60)}`;
  return `${String(date.getFullYear()).padStart(4, '0')}-${two(date.getMonth() + 1)}-${two(date.getDate())}`
    + `T${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}${zone}`;
}

/** Package the selected PDF bytes with the same receipt used by the local archive command. */
export async function createSubmissionArchive(pdfBytes, label, savedAt = new Date()) {
  const slug = labelSlug(label);
  const timestamp = localTimestamp(savedAt);
  if (!(pdfBytes instanceof Uint8Array) || !pdfBytes.length) {
    throw new SubmissionArchiveError('Choose a PDF before saving a submitted copy.');
  }
  // Hash and package the same snapshot even if the caller changes its buffer.
  const pdf = new Uint8Array(pdfBytes);
  const hash = await sha256(pdf);
  const folder = `${timestamp.slice(0, 10)}-${slug}`;
  const pdfName = `resume-${slug}.pdf`;
  const receipt = {
    label: label.trim(),
    saved_at: timestamp,
    pdf: pdfName,
    bytes: pdf.length,
    sha256: hash,
  };
  const zipped = zipSync({
    [`${folder}/${pdfName}`]: pdf,
    [`${folder}/receipt.json`]: encoder.encode(`${JSON.stringify(receipt, null, 2)}\n`),
  }, {
    // The receipt carries the save time; fixed ZIP metadata works for every supported date.
    level: 0, mtime: new Date(2020, 0, 1), os: 3, attrs: 0o100600 << 16,
  });
  return { filename: `${folder}.zip`, blob: new Blob([zipped], { type: 'application/zip' }) };
}
