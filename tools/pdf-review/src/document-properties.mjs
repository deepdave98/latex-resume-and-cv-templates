// Read known fields only. This is an inspection, not metadata removal or a
// complete privacy audit. PDF Info and XMP may contain different values.
const FIELDS = [
  ['Title', 'Title', 'dc:title'],
  ['Author', 'Author', 'dc:creator'],
  ['Subject', 'Subject', 'dc:description'],
  ['Keywords', 'Keywords', 'pdf:keywords'],
  ['Creating application', 'Creator', 'xmp:creatortool'],
  ['PDF producer', 'Producer', 'pdf:producer'],
  ['Created', 'CreationDate', 'xmp:createdate'],
  ['Modified', 'ModDate', 'xmp:modifydate'],
];
const MAX_VALUE_CHARS = 1024;
const MAX_LIST_ITEMS = 16;

function clip(value) {
  const result = value.slice(0, MAX_VALUE_CHARS);
  const last = result.charCodeAt(result.length - 1);
  return last >= 0xd800 && last <= 0xdbff ? result.slice(0, -1) : result;
}

function propertyValue(raw) {
  const values = Array.isArray(raw) ? raw : [raw];
  let limited = values.length > MAX_LIST_ITEMS;
  const parts = [];
  for (let index = 0; index < Math.min(values.length, MAX_LIST_ITEMS); index += 1) {
    const value = values[index];
    if (typeof value !== 'string') {
      if (value != null) limited = true;
      continue;
    }
    const part = clip(value);
    if (part.length < value.length) limited = true;
    if (part.trim()) parts.push(part);
  }
  const joined = parts.join('; ');
  return { value: clip(joined), limited: limited || joined.length > MAX_VALUE_CHARS };
}

export function inspectProperties(data) {
  if (!data || typeof data !== 'object') throw new TypeError('Properties unavailable.');
  const fields = [];
  let limited = false;
  for (const [label, infoKey, xmpKey] of FIELDS) {
    for (const source of ['PDF', 'XMP']) {
      try {
        const raw = source === 'PDF' ? data.info?.[infoKey] : data.metadata?.get(xmpKey);
        const result = propertyValue(raw);
        limited ||= result.limited;
        if (result.value) fields.push({ label, source, value: result.value, limited: result.limited });
      } catch {
        limited = true;
      }
    }
  }
  return { fields, limited };
}

/** A failed or slow metadata read must not discard an otherwise usable review. */
export async function readProperties(pdf, { signal, timeoutMs = 5000 } = {}) {
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 5000) {
    throw new RangeError('Property timeout must be between 1 and 5000 ms.');
  }
  if (signal?.aborted) return { status: 'cancelled', fields: [], limited: false };
  let timer;
  let cancel;
  try {
    const deadline = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('Properties unavailable.')), timeoutMs);
      cancel = () => reject(new Error('Property read cancelled.'));
      signal?.addEventListener('abort', cancel, { once: true });
    });
    const data = await Promise.race([Promise.resolve().then(() => pdf.getMetadata()), deadline]);
    if (signal?.aborted) return { status: 'cancelled', fields: [], limited: false };
    return { status: 'ok', ...inspectProperties(data) };
  } catch {
    return { status: signal?.aborted ? 'cancelled' : 'unavailable', fields: [], limited: false };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}
