// These bounds are separate from PDF extraction limits: a comparison must also
// fit in memory, finish promptly, and produce a manageable amount of UI.
const LIMITS = Object.freeze({ pages: 20, text: 60_000, words: 8_000, cells: 1_000_000,
  runs: 240, output: 80_000, links: 100, destination: 4_096, linkText: 32_000 });
const snapshots = new WeakSet();

function freeze(value) {
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object') freeze(child);
  }
  return Object.freeze(value);
}

/** Copy original extraction data only. No PDF, worker, or editable draft is kept. */
export function createComparisonSnapshot(result, { filename = '', bytes = null } = {}) {
  const pages = Array.isArray(result?.pages) ? result.pages : [];
  const pageCount = Number.isSafeInteger(result?.pageCount) && result.pageCount > 0 ? result.pageCount : null;
  const allPages = pageCount !== null && pageCount <= LIMITS.pages &&
    pages.length === pageCount && result.reviewedPageCount === pageCount;
  const textReasons = new Set();
  const linkReasons = new Set();
  if (!allPages) {
    textReasons.add('Not every page was extracted.');
    linkReasons.add('Not every page was inspected for links.');
  }
  const parts = [];
  const links = [];
  let characters = 0;
  let destinationCharacters = 0;
  let truncationExplained = false;
  for (let index = 0; index < Math.min(pages.length, LIMITS.pages); index += 1) {
    const page = pages[index];
    if (page?.textTruncated || page?.textStatus === 'limited' || page?.linksStatus === 'limited') truncationExplained = true;
    if (page?.number !== index + 1) {
      textReasons.add('The extracted pages are incomplete or out of order.');
      linkReasons.add('The inspected pages are incomplete or out of order.');
    }
    const text = typeof page?.text === 'string' ? page.text : '';
    if (page?.textStatus !== 'ok' || page.textTruncated || !text.slice(0, LIMITS.text + 1).trim()) {
      textReasons.add('A page has missing, empty, or incomplete extracted text.');
    }
    const warnings = Array.isArray(page?.warnings) ? page.warnings : [];
    if (warnings.slice(0, 32).some(warning => warning?.code === 'form-fields')) {
      textReasons.add('Form field values may be absent from the extracted text.');
    }
    if (warnings.slice(0, 32).some(warning => ['text-replacement', 'text-privateUse', 'text-control'].includes(warning?.code))) {
      textReasons.add('Extracted characters need manual review before text can be compared.');
    }
    if (warnings.length > 32) textReasons.add('Too many extraction warnings to assess.');
    const remaining = Math.max(0, LIMITS.text - characters);
    if (text.length > remaining) textReasons.add('Text exceeds the comparison limit.');
    parts.push(text.slice(0, remaining));
    characters += Math.min(text.length, remaining) + 1;
    if (page?.linksStatus !== 'ok' || !Array.isArray(page.links)) {
      linkReasons.add('Link inspection is incomplete.');
    }
    const pageLinks = Array.isArray(page?.links) ? page.links : [];
    for (const link of pageLinks.slice(0, LIMITS.links + 1)) {
      if (link?.truncated) truncationExplained = true;
      if (links.length >= LIMITS.links) {
        linkReasons.add('Links exceed the comparison limit.');
        break;
      }
      if (link?.type !== 'external' || typeof link.destination !== 'string' || !link.destination) {
        linkReasons.add('Internal links, PDF actions, or unknown destinations cannot be compared.');
        continue;
      }
      const resolvedDestination = link.resolvedDestination ?? null;
      if (resolvedDestination !== null && typeof resolvedDestination !== 'string') {
        linkReasons.add('A resolved link destination is unavailable.');
        continue;
      }
      if (link.truncated || link.destination.length > LIMITS.destination || (resolvedDestination?.length ?? 0) > LIMITS.destination) {
        linkReasons.add('A link destination is incomplete.');
        continue;
      }
      const linkCharacters = link.destination.length + (resolvedDestination?.length ?? 0);
      if (destinationCharacters + linkCharacters > LIMITS.linkText) {
        linkReasons.add('Link text exceeds the comparison limit.');
        continue;
      }
      destinationCharacters += linkCharacters;
      links.push({ type: 'external', destination: link.destination, resolvedDestination });
    }
    if (pageLinks.length > LIMITS.links) linkReasons.add('Links exceed the comparison limit.');
  }
  // A top-level truncation flag is authoritative even if an extractor omitted
  // the corresponding per-page detail.
  if (result?.truncated && !truncationExplained) {
    textReasons.add('The PDF review reported incomplete data.');
    linkReasons.add('The PDF review reported incomplete data.');
  }
  const snapshot = freeze({
    filename: typeof filename === 'string' ? filename.slice(0, 255).replace(/[\uD800-\uDBFF]$/u, '') : '',
    bytes: Number.isSafeInteger(bytes) && bytes >= 0 ? bytes : null,
    pageCount,
    text: { value: parts.join('\n'), complete: textReasons.size === 0, reason: [...textReasons].join(' ') },
    links: { values: links, complete: linkReasons.size === 0, reason: [...linkReasons].join(' ') },
  });
  snapshots.add(snapshot);
  return snapshot;
}

function textDifference(before, after) {
  if (!before.complete || !after.complete) {
    return { status: 'incomplete', changes: [], reason: [...new Set([before.reason, after.reason])].filter(Boolean).join(' ') };
  }
  // Whitespace alone is ignored. Do not fold case, strip punctuation, normalize
  // Unicode, or silently rejoin hyphenated words.
  const left = before.value.match(/\S+/gu) ?? [];
  const right = after.value.match(/\S+/gu) ?? [];
  const limited = reason => ({ status: 'limited', changes: [], reason });
  if (left.length > LIMITS.words || right.length > LIMITS.words) return limited('Text has too many words to compare.');
  let start = 0;
  while (start < left.length && start < right.length && left[start] === right[start]) start += 1;
  if (start === left.length && start === right.length) return { status: 'same', changes: [], reason: '' };
  let leftEnd = left.length;
  let rightEnd = right.length;
  while (leftEnd > start && rightEnd > start && left[leftEnd - 1] === right[rightEnd - 1]) {
    leftEnd -= 1;
    rightEnd -= 1;
  }
  const rows = leftEnd - start;
  const columns = rightEnd - start;
  if ((rows + 1) * (columns + 1) > LIMITS.cells) return limited('Too much text changed to display a bounded comparison.');
  const width = columns + 1;
  const lengths = new Uint16Array((rows + 1) * width);
  for (let row = rows - 1; row >= 0; row -= 1) {
    for (let column = columns - 1; column >= 0; column -= 1) {
      lengths[row * width + column] = left[start + row] === right[start + column]
        ? lengths[(row + 1) * width + column + 1] + 1
        : Math.max(lengths[(row + 1) * width + column], lengths[row * width + column + 1]);
    }
  }
  const runs = [];
  function add(type, words) {
    if (!words.length) return;
    const previous = runs.at(-1);
    if (previous?.type === type) previous.words.push(...words);
    else runs.push({ type, words });
  }
  add('equal', left.slice(0, start));
  let row = 0;
  let column = 0;
  while (row < rows || column < columns) {
    if (row < rows && column < columns && left[start + row] === right[start + column]) {
      add('equal', [left[start + row]]); row += 1; column += 1;
    } else if (row < rows && (column === columns || lengths[(row + 1) * width + column] >= lengths[row * width + column + 1])) {
      add('removed', [left[start + row]]); row += 1;
    } else {
      add('added', [right[start + column]]); column += 1;
    }
    if (runs.length > LIMITS.runs) return limited('Too many separate text changes to display.');
  }
  add('equal', left.slice(leftEnd));
  const changes = runs.map(({ type, words }) => ({ type, text: words.join(' ') }));
  if (changes.length > LIMITS.runs || changes.reduce((total, change) => total + change.text.length, 0) > LIMITS.output) {
    return limited('Text changes exceed the display limit.');
  }
  return { status: 'changed', changes, reason: '' };
}

function linkDifference(before, after) {
  const counts = values => {
    const result = new Map();
    for (const link of values) {
      const key = JSON.stringify([link.destination, link.resolvedDestination]);
      const previous = result.get(key);
      if (previous) previous.count += 1;
      else result.set(key, { ...link, count: 1 });
    }
    return result;
  };
  const left = counts(before.values);
  const right = counts(after.values);
  const added = [];
  const removed = [];
  // Compare both raw and resolved destinations: the same relative URL can
  // resolve differently. Preserve schemes and controls as inert display data.
  for (const [key, link] of left) {
    const difference = link.count - (right.get(key)?.count ?? 0);
    if (difference > 0) removed.push({ ...link, count: difference });
  }
  for (const [key, link] of right) {
    const difference = link.count - (left.get(key)?.count ?? 0);
    if (difference > 0) added.push({ ...link, count: difference });
  }
  return { status: !before.complete || !after.complete ? 'incomplete' : added.length || removed.length ? 'changed' : 'same',
    added, removed, reason: [...new Set([before.reason, after.reason])].filter(Boolean).join(' ') };
}

/** Compare extracted text and external destinations, never PDF equivalence. */
export function compareSnapshots(before, after) {
  if (!snapshots.has(before) || !snapshots.has(after)) throw new TypeError('Choose reviewed PDFs to compare.');
  const summary = ({ filename, bytes, pageCount }) => ({ filename, bytes, pageCount });
  return { before: summary(before), after: summary(after),
    text: textDifference(before.text, after.text), links: linkDifference(before.links, after.links) };
}
