// PDF.js supplies the item order. Keep it: this is extraction, not a claim that
// columns, tables, or a hiring system will interpret the document correctly.
const DEFAULTS = Object.freeze({
  maxPages: 20,
  maxTextCharsPerPage: 100_000,
  maxTotalTextChars: 500_000,
  maxTextItemsPerPage: 50_000,
  maxLinksPerPage: 200,
  maxAnnotationsPerPage: 10_000,
  maxDestinationChars: 4_096,
});

function positiveLimit(value, fallback, allowZero = false) {
  if (value === undefined) return fallback;
  if (!Number.isSafeInteger(value) || value < (allowZero ? 0 : 1)) {
    throw new RangeError("Review limits must be whole numbers within range.");
  }
  return Math.min(value, fallback);
}

function clip(value, length) {
  let result = value.slice(0, length);
  const last = result.charCodeAt(result.length - 1);
  if (last >= 0xd800 && last <= 0xdbff) result = result.slice(0, -1);
  return result;
}

function normalizeExtractedText(value) {
  // Full-string NFKC would also change mathematical symbols and other text.
  // Expand only presentation ligatures; preserve the author's other characters.
  return value.replace(/[\uFB00-\uFB06]/gu, (ligature) => ligature.normalize("NFKC"))
    .replace(/\r\n?/gu, "\n")
    .replace(/[\u00A0\u202F]/gu, " ");
}

function hasWordGap(previous, current) {
  if (!previous || previous.hasEOL || previous.dir === "rtl" || current.dir === "rtl") return false;
  if (/\s/u.test(previous.str.slice(-1)) || /\s/u.test(current.str.slice(0, 1))) return false;
  const a = previous.transform;
  const b = current.transform;
  if (!Array.isArray(a) || !Array.isArray(b) || a.length < 6 || b.length < 6) return false;
  if (![...a.slice(0, 6), ...b.slice(0, 6), previous.width].every(Number.isFinite)) return false;
  // Rotated text needs its own coordinate system. Do not guess at its spacing.
  if (Math.abs(a[1]) > 0.01 || Math.abs(a[2]) > 0.01 || Math.abs(b[1]) > 0.01 || Math.abs(b[2]) > 0.01) return false;
  const fontSize = Math.max(Math.abs(a[3]), Math.abs(b[3]), 1);
  if (Math.abs(a[5] - b[5]) > fontSize * 0.2) return false;
  return b[4] - (a[4] + previous.width) >= Math.max(0.5, fontSize * 0.12);
}

/** Read adjacent text items without sorting or introducing spaces inside words. */
export function extractPageText(items, options = {}) {
  const maxChars = positiveLimit(options.maxChars, DEFAULTS.maxTextCharsPerPage, true);
  const maxItems = positiveLimit(options.maxItems, DEFAULTS.maxTextItemsPerPage);
  const chunks = [];
  let length = 0;
  let previous = null;
  let truncated = false;
  let itemLimitReached = false;
  const source = Array.isArray(items) ? items : [];

  for (let index = 0; index < source.length; index += 1) {
    if (index >= maxItems) {
      itemLimitReached = true;
      truncated = true;
      break;
    }
    const item = source[index];
    if (!item || typeof item.str !== "string") continue;
    const separator = item.str && hasWordGap(previous, item) ? " " : "";
    const remaining = maxChars - length;
    // Slice before normalization: a pathological single item cannot allocate an
    // unbounded normalized copy, even if every glyph expands into a ligature.
    const raw = clip(item.str, remaining + 1);
    const addition = separator + normalizeExtractedText(raw) + (item.hasEOL ? "\n" : "");
    if (addition.length > remaining || raw.length < item.str.length) {
      chunks.push(clip(addition, remaining));
      truncated = true;
      break;
    }
    chunks.push(addition);
    length += addition.length;
    if (item.str) previous = item;
    else if (item.hasEOL) previous = null;
  }

  return { text: chunks.join("").trim(), truncated, itemLimitReached };
}

/** These are inspection hints, not errors or a resume score. */
export function inspectTextCharacters(text) {
  const counts = { replacement: 0, privateUse: 0, control: 0, direction: 0 };
  for (const character of text) {
    const code = character.codePointAt(0);
    if (code === 0xfffd) counts.replacement += 1;
    else if ((code >= 0xe000 && code <= 0xf8ff) || (code >= 0xf0000 && code <= 0xffffd) || (code >= 0x100000 && code <= 0x10fffd)) counts.privateUse += 1;
    else if ((code < 0x20 && ![9, 10, 13].includes(code)) || (code >= 0x7f && code <= 0x9f)) counts.control += 1;
    else if ((code >= 0x202a && code <= 0x202e) || (code >= 0x2066 && code <= 0x2069)) counts.direction += 1;
  }
  const messages = {
    replacement: "Replacement characters appear in the extracted text. Compare them with the page.",
    privateUse: "Private-use characters appear in the extracted text. Icons or custom fonts may not copy as expected.",
    control: "Control characters appear in the extracted text. Check the text after pasting it into a form.",
    direction: "Text-direction controls appear in the extracted text. They can be valid, but pasted text may display differently.",
  };
  return Object.entries(counts).filter(([, count]) => count > 0)
    .map(([kind, count]) => ({ code: `text-${kind}`, message: messages[kind], count }));
}

function destinationText(value, maxChars) {
  if (typeof value === "string") return clip(value, maxChars);
  if (Number.isFinite(value)) return String(value);
  return "";
}

const HIDDEN_DESTINATION_CHARACTER = /[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]/u;

/** Show hidden controls literally; callers must still insert this as text. */
export function displayDestination(value) {
  if (typeof value !== "string") return "";
  return value.replace(new RegExp(HIDDEN_DESTINATION_CHARACTER.source, "gu"), (character) => {
    const code = character.codePointAt(0);
    return code <= 0xffff ? `\\u${code.toString(16).padStart(4, "0")}` : `\\u{${code.toString(16)}}`;
  });
}

function internalDestination(destination, maxChars) {
  if (typeof destination === "string") return `Named destination: ${clip(destination, maxChars)}`;
  if (Array.isArray(destination)) {
    const target = destination[0];
    if (Number.isInteger(target) && target >= 0) return `Page ${target + 1}`;
    if (target && Number.isSafeInteger(target.num) && Number.isSafeInteger(target.gen)) {
      return `PDF object ${target.num} ${target.gen} R`;
    }
  }
  return "Unresolved internal destination";
}

// Match only contacts shipped in the starters, not names or generic words in
// someone's resume. Ignore URL query/fragment additions, but require the host
// and profile path to match; a substring check would flag unrelated links.
function isSampleContact(destination) {
  try {
    const url = new URL(destination);
    const path = decodeURIComponent(url.pathname);
    if (url.protocol === "mailto:") return path.toLowerCase() === "hello@example.com";
    if (url.protocol === "tel:") return path.replace(/[\s().-]/gu, "") === "+15555555555";
    if (url.protocol !== "https:" && url.protocol !== "http:") return false;
    const host = url.hostname.replace(/^www\./u, "");
    const profile = path.toLowerCase().replace(/\/+$/u, "");
    return (host === "github.com" && profile === "/your-handle")
      || (host === "linkedin.com" && profile === "/in/your-handle");
  } catch {
    return false;
  }
}

/** Return inert data only. Never turn annotations into HTML or execute actions. */
export function inspectLinkAnnotations(annotations, options = {}) {
  const maxLinks = positiveLimit(options.maxLinks, DEFAULTS.maxLinksPerPage);
  const maxAnnotations = positiveLimit(options.maxAnnotations, DEFAULTS.maxAnnotationsPerPage);
  const maxChars = positiveLimit(options.maxDestinationChars, DEFAULTS.maxDestinationChars);
  const source = Array.isArray(annotations) ? annotations : [];
  const links = [];
  let truncated = false;
  let formFieldCount = 0;

  for (let index = 0; index < source.length; index += 1) {
    if (index >= maxAnnotations) { truncated = true; break; }
    const annotation = source[index];
    if (annotation?.annotationType === 20 || annotation?.subtype === "Widget") formFieldCount += 1;
    if (!annotation || (annotation.annotationType !== 2 && annotation.subtype !== "Link")) continue;
    if (links.length >= maxLinks) { truncated = true; break; }
    const rect = Array.isArray(annotation.rect) && annotation.rect.length === 4 && annotation.rect.every(Number.isFinite)
      ? [...annotation.rect] : null;
    const base = { rect, label: destinationText(annotation.contentsObj?.str, maxChars) };
    const rawUrl = typeof annotation.unsafeUrl === "string" ? annotation.unsafeUrl : annotation.url;
    if (typeof rawUrl === "string") {
      const destination = clip(rawUrl, maxChars);
      const resolvedDestination = typeof annotation.url === "string" ? clip(annotation.url, maxChars) : null;
      const hiddenCharacters = HIDDEN_DESTINATION_CHARACTER.test(destination) || HIDDEN_DESTINATION_CHARACTER.test(resolvedDestination ?? "");
      const destinationTruncated = rawUrl.length > maxChars || (annotation.url?.length ?? 0) > maxChars;
      const sampleContact = !destinationTruncated && (isSampleContact(destination) || isSampleContact(resolvedDestination));
      let protocol = null;
      try { protocol = new URL(destination).protocol; } catch { /* Relative and malformed destinations stay visible. */ }
      const unsafe = hiddenCharacters || destinationTruncated || !protocol || !["https:", "http:", "mailto:", "tel:"].includes(protocol);
      links.push({ ...base, type: "external", destination, resolvedDestination, unsafe, hiddenCharacters, sampleContact,
        truncated: destinationTruncated,
        reason: hiddenCharacters ? "Contains hidden control or direction characters. Inspect the visible Unicode escapes in this destination."
          : (unsafe ? "Unrecognized, incomplete, or potentially unsafe destination. Shown as text only." : "") });
    } else if (annotation.dest !== undefined && annotation.dest !== null) {
      links.push({ ...base, type: "internal", destination: internalDestination(annotation.dest, maxChars),
        unsafe: false, truncated: typeof annotation.dest === "string" && annotation.dest.length > maxChars,
        reason: "Links to a location inside this PDF." });
    } else if (annotation.action || annotation.actions || annotation.isTooltipOnly || annotation.resetForm || annotation.setOCGState) {
      links.push({ ...base, type: "action", destination: destinationText(annotation.action, maxChars) || "PDF action",
        unsafe: true, truncated: typeof annotation.action === "string" && annotation.action.length > maxChars,
        reason: "PDF actions are not executed by this tool." });
    } else {
      links.push({ ...base, type: "unknown", destination: "Destination unavailable", unsafe: true, truncated: false,
        reason: "PDF.js did not expose a destination. The tool cannot verify this link." });
    }
  }
  return { links, truncated, formFieldCount };
}

function checkCancelled(signal) {
  if (!signal?.aborted) return;
  const error = new Error("Review cancelled.");
  error.name = "AbortError";
  throw error;
}

/** Review an already-open PDF.js document. The caller owns its lifecycle. */
export async function reviewDocument(pdf, options = {}) {
  if (!Number.isSafeInteger(pdf?.numPages) || pdf.numPages < 1 || typeof pdf.getPage !== "function") {
    throw new TypeError("A readable PDF document is required.");
  }
  const limits = Object.fromEntries(Object.entries(DEFAULTS)
    .map(([name, fallback]) => [name, positiveLimit(options[name], fallback)]));
  const pages = [];
  const warnings = [];
  const pageLimit = Math.min(pdf.numPages, limits.maxPages);
  let remainingText = limits.maxTotalTextChars;
  if (pdf.numPages > pageLimit) warnings.push({ code: "page-limit", message: `Only the first ${pageLimit} pages were reviewed.` });

  for (let number = 1; number <= pageLimit; number += 1) {
    checkCancelled(options.signal);
    const result = { number, text: "", hasText: false, textStatus: "error", textTruncated: false,
      links: [], linksStatus: "error", warnings: [] };
    let page;
    try {
      page = await pdf.getPage(number);
    } catch {
      checkCancelled(options.signal);
      result.warnings.push({ code: "page-read-failed", message: "This page could not be read. It has not been checked for text or links." });
    }
    checkCancelled(options.signal);
    if (page) {
      try {
        const content = await page.getTextContent();
        checkCancelled(options.signal);
        const extracted = extractPageText(content.items, { maxChars: Math.min(remainingText, limits.maxTextCharsPerPage), maxItems: limits.maxTextItemsPerPage });
        result.text = extracted.text;
        result.hasText = extracted.text.length > 0;
        result.textTruncated = extracted.truncated;
        result.textStatus = extracted.truncated ? "limited" : (result.hasText ? "ok" : "empty");
        remainingText -= result.text.length;
        result.warnings.push(...inspectTextCharacters(result.text));
        if (extracted.truncated) result.warnings.push({ code: "text-limit", message: "Extracted text was cut short at the review limit. Some content has not been checked." });
        if (!result.hasText && !extracted.truncated) result.warnings.push({ code: "no-extracted-text", message: "No extractable text was found. This can be an image, a scanned page, or an empty page; inspect the preview." });
      } catch {
        checkCancelled(options.signal);
        result.warnings.push({ code: "text-extraction-failed", message: "Text extraction failed for this page. This does not mean the page is empty." });
      }
      try {
        const annotations = await page.getAnnotations({ intent: "display" });
        checkCancelled(options.signal);
        const inspected = inspectLinkAnnotations(annotations, { maxLinks: limits.maxLinksPerPage, maxAnnotations: limits.maxAnnotationsPerPage, maxDestinationChars: limits.maxDestinationChars });
        result.links = inspected.links;
        result.linksStatus = inspected.truncated ? "limited" : "ok";
        if (inspected.formFieldCount) result.warnings.push({ code: "form-fields", message: "This page has form fields. Field values may be missing from extracted text; check the preview and the original PDF." });
        if (inspected.truncated) result.warnings.push({ code: "link-limit", message: "Some annotations exceeded the review limit. Not all links have been inspected." });
        if (inspected.links.some((link) => link.truncated)) result.warnings.push({ code: "destination-limit", message: "Long link destinations were cut short for display. Their full values have not been inspected." });
      } catch {
        checkCancelled(options.signal);
        result.warnings.push({ code: "link-extraction-failed", message: "Link inspection failed for this page. This does not mean the page has no links." });
      }
    }
    pages.push(result);
    if (typeof options.onProgress === "function") options.onProgress({ pageNumber: number, pageCount: pageLimit });
  }
  return { pages, text: pages.map((page) => page.text).join("\n\n"), pageCount: pdf.numPages,
    reviewedPageCount: pages.length, linkCount: pages.reduce((count, page) => count + page.links.length, 0),
    sampleLinkCount: pages.reduce((count, page) => count + page.links.filter((link) => link.sampleContact).length, 0),
    emptyTextPageCount: pages.filter((page) => page.textStatus === "empty").length,
    truncated: pdf.numPages > pageLimit || pages.some((page) => page.textTruncated || page.linksStatus === "limited" || page.links.some((link) => link.truncated)), warnings };
}
