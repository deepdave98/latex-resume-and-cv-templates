// Compare with limits supplied by the applicant, not a built-in resume policy.
// MB is decimal. Convert the typed value to whole bytes before comparing so
// display rounding cannot make a file one byte over the limit appear to fit.
function parseLimit(value, kind) {
  const text = String(value ?? '').trim();
  if (!text) return { status: 'unset' };
  const pattern = kind === 'pages' ? /^\d+$/u : /^\d+(?:\.\d{1,6})?$/u;
  if (text.length > 32 || !pattern.test(text)) return { status: 'invalid' };
  const [whole, fraction = ''] = text.split('.');
  const limit = kind === 'pages'
    ? Number(whole)
    : Number(whole) * 1_000_000 + Number(fraction.padEnd(6, '0'));
  return Number.isSafeInteger(limit) && limit > 0
    ? { status: 'set', limit }
    : { status: 'invalid' };
}

function compare(actual, value, kind) {
  const parsed = parseLimit(value, kind);
  if (parsed.status !== 'set') return parsed;
  if (!Number.isSafeInteger(actual) || actual < 1) return { ...parsed, status: 'unknown' };
  return { limit: parsed.limit, status: actual > parsed.limit ? 'over' : 'within' };
}

export function checkUploadLimits({ bytes, pages }, { maxPages = '', maxMB = '' } = {}) {
  return {
    pages: compare(pages, maxPages, 'pages'),
    size: compare(bytes, maxMB, 'size'),
  };
}

export function formatFileSize(bytes) {
  if (!Number.isSafeInteger(bytes) || bytes < 0) return 'File size unavailable';
  // Keep the exact byte count beside the abbreviated size.
  return `${(bytes / 1_000_000).toFixed(2)} MB (${bytes.toLocaleString('en-US')} bytes)`;
}
