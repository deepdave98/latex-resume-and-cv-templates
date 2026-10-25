import assert from "node:assert/strict";
import test from "node:test";
import { displayDestination, extractPageText, inspectLinkAnnotations, inspectTextCharacters, reviewDocument } from "../src/review.mjs";

const item = (str, x = 0, width = 10, hasEOL = false, extra = {}) => ({ str, transform: [10, 0, 0, 10, x, 100], width, hasEOL, ...extra });
const link = (properties) => ({ annotationType: 2, ...properties });
const page = (items = [], annotations = []) => ({
  getTextContent: async () => ({ items }),
  getAnnotations: async (options) => { assert.deepEqual(options, { intent: "display" }); return annotations; },
});
const document = (pages) => ({ numPages: pages.length, getPage: async (number) => pages[number - 1] });

test("text keeps PDF item order, explicit line breaks, and adjacent word pieces", () => {
  const result = extractPageText([item("Back", 0, 20), item("end", 20, 15), item("engineer", 38, 40, true), item("Second line", 0, 50)]);
  assert.equal(result.text, "Backend engineer\nSecond line");
  assert.equal(result.truncated, false);
  assert.equal(extractPageText([item("Right", 100, 20, true), item("Left", 0)]).text, "Right\nLeft");
});

test("spaces are inferred only from reliable adjacent geometry", () => {
  assert.equal(extractPageText([{ str: "soft" }, { str: "ware" }]).text, "software");
  assert.equal(extractPageText([item("soft", 0, 20), item("ware", 20.1)]).text, "software");
  assert.equal(extractPageText([item("two "), item(" words", 50)]).text, "two  words");
  assert.equal(extractPageText([item("abc"), item("def", 90, 10, false, { dir: "rtl" })]).text, "abcdef");
  assert.equal(extractPageText([item("abc"), item("def", 90, 10, false, { transform: [0, 10, -10, 0, 90, 100] })]).text, "abcdef");
});

test("ligatures and nonbreaking spaces normalize without changing mathematical or fullwidth text", () => {
  assert.equal(extractPageText([{ str: "ﬁx ﬂow ﬀi ﬃ ﬄ ﬅ ﬆ\u00a0A\u202fB ² ① Ａ\r\nnext" }]).text, "fix flow ffi ffi ffl st st A B ² ① Ａ\nnext");
});

test("empty and non-text marked-content items do not invent text", () => {
  assert.equal(extractPageText([{ type: "beginMarkedContent" }, { str: "", hasEOL: true }, { str: "  " }]).text, "");
  assert.equal(extractPageText([item("one"), { str: "", hasEOL: true }, item("two", 50)]).text, "one\ntwo");
});

test("text limits bound huge items, expanded ligatures, item counts, and surrogate pairs", () => {
  assert.deepEqual(extractPageText([{ str: "a".repeat(1_000_000) }], { maxChars: 8 }), { text: "aaaaaaaa", truncated: true, itemLimitReached: false });
  assert.equal(extractPageText([{ str: "ﬃ".repeat(100) }], { maxChars: 4 }).text, "ffif");
  assert.equal(extractPageText([{ str: "a😀z" }], { maxChars: 2 }).text, "a");
  assert.equal(extractPageText([{ str: "yes" }], { maxChars: 0 }).truncated, true);
  assert.deepEqual(extractPageText([{ str: "" }, { str: "" }, { str: "hidden" }], { maxItems: 2 }), { text: "", truncated: true, itemLimitReached: true });
});

test("invalid limits fail with generic messages", () => {
  for (const maxChars of [-1, NaN, Infinity, 1.5, "10"]) assert.throws(() => extractPageText([], { maxChars }), RangeError);
  assert.throws(() => inspectLinkAnnotations([], { maxLinks: 0 }), RangeError);
});

test("character inspection distinguishes private use, replacement, controls, and bidi", () => {
  const warnings = inspectTextCharacters("normal\n\t α�\uE000\u{F0001}\u0000\u0080\u202e\u2066");
  assert.deepEqual(warnings.map(({ code, count }) => [code, count]), [["text-replacement", 1], ["text-privateUse", 2], ["text-control", 2], ["text-direction", 2]]);
  assert.deepEqual(inspectTextCharacters("José 李 أحمد 100%\n\t"), []);
});

test("external links preserve raw and resolved destinations as inert strings", () => {
  const raw = "https://example.test/<img src=x onerror=alert(1)>";
  const result = inspectLinkAnnotations([link({ unsafeUrl: raw, url: "https://example.test/%3Cimg%20src=x%20onerror=alert(1)%3E", rect: [1, 2, 3, 4], contentsObj: { str: "<script>bad()</script>" } })]);
  assert.equal(result.links[0].destination, raw);
  assert.equal(result.links[0].label, "<script>bad()</script>");
  assert.equal(result.links[0].unsafe, false);
  assert.deepEqual(result.links[0].rect, [1, 2, 3, 4]);
  assert.notEqual(result.links[0].resolvedDestination, raw);
});

test("unsafe, malformed, and relative destinations stay visible but are flagged", () => {
  for (const destination of ["javascript:alert(1)", "data:text/html,hello", "file:///private/resume", "ftp://example.test", "../../relative", "not a url", ""]) {
    const [result] = inspectLinkAnnotations([link({ unsafeUrl: destination })]).links;
    assert.equal(result.destination, destination);
    assert.equal(result.unsafe, true);
  }
  for (const destination of ["https://example.test", "http://example.test", "mailto:person@example.test", "tel:+15551234567"]) {
    assert.equal(inspectLinkAnnotations([link({ url: destination })]).links[0].unsafe, false);
  }
});

test("known starter contacts are flagged across URL formatting variations", () => {
  for (const destination of [
    "mailto:hello@example.com", "MAILTO:hello%40example.com?subject=Resume",
    "tel:+15555555555", "tel:%2B1%20(555)%20555-5555",
    "https://github.com/your-handle", "http://www.github.com/Your-Handle/?tab=repositories",
    "https://github.com/%79our-handle#readme",
    "https://www.linkedin.com/in/your-handle", "https://linkedin.com/in/your-handle/?trk=resume",
  ]) {
    const [result] = inspectLinkAnnotations([link({ url: destination })]).links;
    assert.equal(result.sampleContact, true, destination);
    assert.equal(result.destination, destination);
    assert.equal(result.unsafe, false, "a sample is not an unsafe URL");
  }
});

test("sample checks do not guess from labels, partial names, unrelated hosts, or query text", () => {
  for (const destination of [
    "mailto:alex@example.test", "mailto:hello@example.com.test", "mailto:hello+jobs@example.com",
    "tel:+15555550123", "tel:+25555555555", "tel:+155555555550",
    "https://github.com/alex-morgan", "https://github.com/your-handle-project",
    "https://github.com/alex/your-handle", "https://github.com/?next=/your-handle",
    "https://github.com/your-handle/repository", "https://notgithub.com/your-handle",
    "https://github.com.example.test/your-handle", "https://github.com@elsewhere.test/your-handle",
    "https://linkedin.com/company/your-handle", "https://linkedin.com/in/your-handle-team",
    "https://www.linkedin.com/in/alex", "https://github.com/%zz",
    "https://example.test/your-handle", "ftp://github.com/your-handle", "github.com/your-handle",
  ]) {
    const [result] = inspectLinkAnnotations([link({ url: destination, contentsObj: { str: "hello@example.com" } })]).links;
    assert.equal(result.sampleContact, false, destination);
  }
});

test("sample checks inspect raw and resolved destinations without replacing security warnings", () => {
  const raw = "https://github.com/your-handle";
  const resolved = "https://www.linkedin.com/in/your-handle";
  const results = inspectLinkAnnotations([
    link({ unsafeUrl: raw, url: "https://elsewhere.test/" }),
    link({ unsafeUrl: "/in/your-handle", url: resolved }),
    link({ unsafeUrl: "https://github.com/your-\nhandle", url: raw }),
  ]).links;
  assert.ok(results.every((result) => result.sampleContact));
  assert.equal(results[0].destination, raw);
  assert.equal(results[1].unsafe, true);
  assert.equal(results[1].resolvedDestination, resolved);
  assert.match(results[2].reason, /hidden control/u);
});

test("a truncated link is not mistaken for a complete sample destination", () => {
  const prefix = "https://github.com/your-handle";
  const [result] = inspectLinkAnnotations([link({ url: `${prefix}-real` })], { maxDestinationChars: prefix.length }).links;
  assert.equal(result.destination, prefix);
  assert.equal(result.truncated, true);
  assert.equal(result.sampleContact, false);
});

test("sample counts include link annotations only, across all reviewed pages", async () => {
  const result = await reviewDocument(document([
    page([item("hello@example.com")], [link({ url: "https://github.com/alex" })]),
    page([], [link({ url: "mailto:hello@example.com" }), link({ url: "tel:+15555555555" }), link({ dest: "hello@example.com" })]),
  ]));
  assert.equal(result.sampleLinkCount, 2);
  assert.equal(result.linkCount, 4);
  assert.equal(result.pages[0].links[0].sampleContact, false);
  assert.equal(result.truncated, false);
});

test("URL controls cannot disappear through URL parsing or spoof displayed destinations", () => {
  for (const character of ["\n", "\t", "\r", "\u0000", "\u0085", "\u00ad", "\u061c", "\u200b", "\u200e", "\u2028", "\u2029", "\u202e", "\u2066", "\ufeff", "\u{e0001}"]) {
    const destination = `https://example.test/${character}secret`;
    const inspected = inspectLinkAnnotations([link({ unsafeUrl: destination, url: "https://example.test/secret" })]).links[0];
    assert.equal(inspected.destination, destination);
    assert.equal(inspected.hiddenCharacters, true);
    assert.equal(inspected.unsafe, true);
    assert.match(inspected.reason, /hidden control or direction characters/u);
    assert.equal(displayDestination(inspected.destination).includes(character), false);
    assert.match(displayDestination(inspected.destination), /\\u(?:[0-9a-f]{4}|\{[0-9a-f]+\})secret$/u);
  }
  assert.equal(displayDestination("https://example.test/\u202e\n\t"), "https://example.test/\\u202e\\u000a\\u0009");
  assert.equal(displayDestination("https://example.test/\u{e0001}"), "https://example.test/\\u{e0001}");
});

test("resolved destinations are checked separately and readable destinations are unchanged", () => {
  const result = inspectLinkAnnotations([link({ unsafeUrl: "https://example.test/ok", url: "https://example.test/\u202ebad" })]).links[0];
  assert.equal(result.hiddenCharacters, true);
  assert.equal(result.unsafe, true);
  assert.equal(displayDestination(result.resolvedDestination), "https://example.test/\\u202ebad");
  assert.equal(displayDestination("https://example.test/José/李?q=<script>"), "https://example.test/José/李?q=<script>");
  assert.equal(displayDestination(null), "");
  assert.equal(inspectLinkAnnotations([link({ url: "https://example.test" })]).links[0].hiddenCharacters, false);
});

test("internal links and PDF actions are not confused with web URLs", () => {
  const inspected = inspectLinkAnnotations([
    link({ dest: "chapter-one" }), link({ dest: [2, { name: "XYZ" }, 0, 0, null] }),
    link({ dest: [{ num: 8, gen: 0 }, { name: "Fit" }] }),
    link({ action: "NextPage" }), link({ actions: { Action: ["app.alert('no')"] } }), link({}),
    { annotationType: 1, contentsObj: { str: "not a link" } },
  ]);
  assert.deepEqual(inspected.links.map(({ type }) => type), ["internal", "internal", "internal", "action", "action", "unknown"]);
  assert.equal(inspected.links[1].destination, "Page 3");
  assert.equal(inspected.links[2].destination, "PDF object 8 0 R");
  assert.equal(inspected.links[4].destination, "PDF action");
  assert.equal(JSON.stringify(inspected).includes("app.alert"), false);
});

test("annotation bounds include non-links and long destination text", () => {
  const countLimited = inspectLinkAnnotations([link({ url: "https://one.test" }), link({ url: "https://two.test" })], { maxLinks: 1 });
  assert.equal(countLimited.links.length, 1);
  assert.equal(countLimited.truncated, true);
  assert.equal(inspectLinkAnnotations([{}, {}, link({ url: "https://hidden.test" })], { maxAnnotations: 2 }).truncated, true);
  const long = inspectLinkAnnotations([link({ url: "https://example.test/" + "a".repeat(10_000), rect: [1, NaN, 3, 4] })], { maxDestinationChars: 30 }).links[0];
  assert.equal(long.destination.length, 30);
  assert.equal(long.truncated, true);
  assert.equal(long.rect, null);
});

test("document review supplies page text, links, progress, and combined form text", async () => {
  const progress = [];
  const result = await reviewDocument(document([page([item("First")], [link({ url: "https://example.test" })]), page([item("Second")])]), { onProgress: (value) => progress.push(value) });
  assert.equal(result.text, "First\n\nSecond");
  assert.equal(result.linkCount, 1);
  assert.equal(result.pageCount, 2);
  assert.equal(result.reviewedPageCount, 2);
  assert.equal(result.truncated, false);
  assert.deepEqual(result.pages.map(({ number, textStatus, linksStatus }) => [number, textStatus, linksStatus]), [[1, "ok", "ok"], [2, "ok", "ok"]]);
  assert.deepEqual(progress, [{ pageNumber: 1, pageCount: 2 }, { pageNumber: 2, pageCount: 2 }]);
});

test("form widgets are flagged because their values may not be in page text", async () => {
  const result = await reviewDocument(document([page([item("Name:")], [{ annotationType: 20, fieldValue: "Private value" }])]));
  assert.equal(result.pages[0].warnings[0].code, "form-fields");
  assert.equal(result.linkCount, 0);
  assert.equal(result.text.includes("Private value"), false);
});

test("no text never claims a page is visually blank", async () => {
  const result = await reviewDocument(document([page()]));
  assert.equal(result.pages[0].textStatus, "empty");
  assert.equal(result.emptyTextPageCount, 1);
  assert.match(result.pages[0].warnings[0].message, /image, a scanned page, or an empty page/u);
  assert.equal("isBlank" in result.pages[0], false);
});

test("per-page failures remain distinct from empty text and missing links without leaking parser errors", async () => {
  const secret = "Private resume text https://private.example";
  const result = await reviewDocument({ numPages: 3, getPage: async (number) => {
    if (number === 1) throw new Error(secret);
    if (number === 2) return { getTextContent: async () => { throw new Error(secret); }, getAnnotations: async () => { throw new Error(secret); } };
    return page([item("Recovered")]);
  } });
  assert.equal(result.pages[0].textStatus, "error");
  assert.equal(result.pages[1].textStatus, "error");
  assert.equal(result.pages[1].linksStatus, "error");
  assert.equal(result.emptyTextPageCount, 0);
  assert.equal(result.pages[2].text, "Recovered");
  assert.equal(JSON.stringify(result).includes(secret), false);
  assert.deepEqual(result.pages[1].warnings.map(({ code }) => code), ["text-extraction-failed", "link-extraction-failed"]);
});

test("review bounds pages and total output and signals every incomplete result", async () => {
  const result = await reviewDocument(document([page([item("123456")]), page([item("abcdef")]), page([item("not read")])]), { maxPages: 2, maxTotalTextChars: 8 });
  assert.equal(result.reviewedPageCount, 2);
  assert.equal(result.pages[1].text, "ab");
  assert.equal(result.pages[1].textStatus, "limited");
  assert.equal(result.truncated, true);
  assert.equal(result.warnings[0].code, "page-limit");
  const links = await reviewDocument(document([page([], [link({ url: "https://one.test" }), link({ url: "https://two.test" })])]), { maxLinksPerPage: 1 });
  assert.equal(links.pages[0].linksStatus, "limited");
  assert.equal(links.truncated, true);
});

test("cancellation stops before opening pages and during a pending extraction", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(reviewDocument({ numPages: 1, getPage: () => { assert.fail("should not read"); } }, { signal: controller.signal }), { name: "AbortError" });
  const during = new AbortController();
  await assert.rejects(reviewDocument(document([{ getTextContent: async () => { during.abort(); return { items: [] }; }, getAnnotations: () => { assert.fail("should stop"); } }]), { signal: during.signal }), { name: "AbortError" });
});

test("invalid document inputs are rejected before processing", async () => {
  for (const value of [null, {}, { numPages: 0, getPage() {} }, { numPages: Infinity, getPage() {} }]) {
    await assert.rejects(reviewDocument(value), TypeError);
  }
});
