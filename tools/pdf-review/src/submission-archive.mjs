import { zipSync } from 'fflate';

const encoder = new TextEncoder();

export class SubmissionArchiveError extends Error {}

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
  if (typeof globalThis.crypto?.subtle?.digest !== 'function') {
    throw new SubmissionArchiveError('SHA-256 is unavailable. Open the downloaded reviewer in a current browser.');
  }
  // Hash and package the same snapshot even if the caller changes its buffer.
  const pdf = new Uint8Array(pdfBytes);
  let digest;
  try {
    digest = await globalThis.crypto.subtle.digest('SHA-256', pdf);
  } catch {
    throw new Error('Could not calculate the PDF hash. Try again in a current browser.');
  }
  const folder = `${timestamp.slice(0, 10)}-${slug}`;
  const pdfName = `resume-${slug}.pdf`;
  const receipt = {
    label: label.trim(),
    saved_at: timestamp,
    pdf: pdfName,
    bytes: pdf.length,
    sha256: Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join(''),
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
