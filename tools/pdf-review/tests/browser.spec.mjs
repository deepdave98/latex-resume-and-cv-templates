import { test, expect } from "@playwright/test";
import { readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { encryptedFixture, filePayload, pdfFixture } from "./fixtures.mjs";

const artifactURL = new URL("../../../downloads/pdf-review.html", import.meta.url).href;
const resumePath = (name) => fileURLToPath(new URL(`../../../output/pdf/${name}.pdf`, import.meta.url));
const publishedPDFs = readdirSync(new URL("../../../output/pdf/", import.meta.url))
  .filter((name) => name.endsWith(".pdf")).sort();

async function openReview(page, context, location = "/") {
  const errors = [];
  const requests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const webkit = context.browser().browserType().name() === "webkit";
  if (location.startsWith("file:") && !webkit) await context.setOffline(true);
  await page.goto(location);
  await expect(page.locator("#pdf-file")).toBeAttached();
  // The initial HTML request is expected. Everything after that must be local,
  // including the PDF worker, fonts, CMaps, and image decoders.
  context.on("request", (request) => {
    if (/^https?:/.test(request.url())) requests.push(request.url());
  });
  // Playwright's WebKit offline emulation also blocks local blob workers.
  // Block HTTP(S) instead, and still assert that the app never attempts one.
  // Chromium and Firefox also exercise the browser's full offline emulation.
  if (webkit) await context.route(/^https?:\/\//, (route) => route.abort());
  else await context.setOffline(true);
  return { errors, requests };
}

async function reviewFile(page, payload) {
  await page.locator("#pdf-file").setInputFiles(payload);
  await page.waitForFunction(() => document.getElementById("status").textContent === "Review ready." || !document.getElementById("error").hidden, null, { timeout: 30_000 });
  expect(await page.locator("#status").textContent(), await page.locator("#error").textContent()).toBe("Review ready.");
  await expect(page.locator("#error")).toBeHidden();
  await expect(page.locator("#review")).toBeVisible();
}

async function assertPrivate(context, page, observations) {
  expect(observations.requests).toEqual([]);
  expect(observations.errors).toEqual([]);
  expect(await context.cookies()).toEqual([]);
  const storage = await page.evaluate(async () => {
    const values = {};
    for (const kind of ["localStorage", "sessionStorage"]) {
      try { values[kind] = window[kind].length; } catch { values[kind] = 0; }
    }
    try { values.databases = (await indexedDB.databases()).length; } catch { values.databases = 0; }
    return values;
  });
  expect(storage).toEqual({ localStorage: 0, sessionStorage: 0, databases: 0 });
}

async function assertHighlightGeometry(card, expected) {
  const geometry = await card.evaluate((node) => {
    const canvas = node.querySelector("canvas");
    const overlay = node.querySelector(".link-overlay");
    const highlight = overlay.querySelector(".link-highlight");
    const bounds = (element) => {
      const { x, y, width, height } = element.getBoundingClientRect();
      return { x, y, width, height };
    };
    // Firefox includes the non-scaling stroke in getBoundingClientRect. Project
    // the SVG fill box so every engine checks the same annotation geometry.
    const box = highlight.getBBox();
    const matrix = highlight.getScreenCTM();
    const start = new DOMPoint(box.x, box.y).matrixTransform(matrix);
    const end = new DOMPoint(box.x + box.width, box.y + box.height).matrixTransform(matrix);
    return {
      canvas: bounds(canvas), overlay: bounds(overlay),
      highlight: { x: start.x, y: start.y, width: end.x - start.x, height: end.y - start.y },
      viewBox: overlay.getAttribute("viewBox").split(/\s+/).map(Number),
      attributes: Object.fromEntries(["x", "y", "width", "height"].map((key) => [key, Number(highlight.getAttribute(key))])),
    };
  });
  const scale = geometry.viewBox[2] / expected.pageWidth;
  expect(geometry.viewBox[0]).toBe(0);
  expect(geometry.viewBox[1]).toBe(0);
  expect(geometry.viewBox[3]).toBeCloseTo(expected.pageHeight * scale, 5);
  for (const key of ["x", "y", "width", "height"]) {
    expect(geometry.attributes[key], `PDF viewport ${key}`).toBeCloseTo(expected[key] * scale, 5);
    expect(geometry.overlay[key], `overlay covers canvas ${key}`).toBeCloseTo(geometry.canvas[key], 0);
  }
  const displayed = {
    x: geometry.canvas.x + expected.x / expected.pageWidth * geometry.canvas.width,
    y: geometry.canvas.y + expected.y / expected.pageHeight * geometry.canvas.height,
    width: expected.width / expected.pageWidth * geometry.canvas.width,
    height: expected.height / expected.pageHeight * geometry.canvas.height,
  };
  for (const key of ["x", "y", "width", "height"]) {
    expect(Math.abs(geometry.highlight[key] - displayed[key]), `displayed highlight ${key}`).toBeLessThan(1);
  }
}

for (const [label, location] of [["downloaded file", artifactURL], ["hosted page", "/"]]) {
  test(`${label}: reviews the one-page starter without network access`, async ({ page, context }) => {
    const observations = await openReview(page, context, location);
    await reviewFile(page, resumePath("new-grad-resume"));
    await expect(page.locator(".page-card")).toHaveCount(1);
    await expect(page.locator("#all-text")).toHaveValue(/Education/i);
    await expect(page.locator("#all-text")).toHaveValue(/Experience/i);
    await expect(page.locator("#pages")).toContainText("mailto:");
    await expect(page.locator("#pages canvas")).toHaveCount(1);
    expect(await page.locator("#pages canvas").evaluate((canvas) => canvas.width > 0 && canvas.height > 0)).toBe(true);
    await assertPrivate(context, page, observations);
  });
}

for (const filename of publishedPDFs) {
  test(`renders every page of published ${filename}`, async ({ page, context }) => {
    const observations = await openReview(page, context, artifactURL);
    await reviewFile(page, resumePath(filename.slice(0, -4)));
    const cards = page.locator(".page-card");
    expect(await cards.count()).toBeGreaterThan(0);
    for (const card of await cards.all()) {
      expect((await card.locator("textarea").inputValue()).trim().length).toBeGreaterThan(100);
      const canvas = card.locator("canvas");
      await expect(canvas).toBeVisible();
      const hasInk = await canvas.evaluate((element) => {
        const pixels = element.getContext("2d").getImageData(0, 0, element.width, element.height).data;
        // Reject empty or white-only renders, even when text extraction worked.
        for (let i = 0; i < pixels.length; i += 4) {
          if (pixels[i + 3] > 0 && pixels[i] < 200 && pixels[i + 1] < 200 && pixels[i + 2] < 200) return true;
        }
        return false;
      });
      expect(hasInk, `${filename}: page has rendered content`).toBe(true);
    }
    await assertPrivate(context, page, observations);
  });
}

test("reviews both pages of the experienced starter", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, resumePath("experienced-resume"));
  await expect(page.locator(".page-card")).toHaveCount(2);
  const pages = await page.locator(".page-card textarea").evaluateAll((fields) => fields.map((field) => field.value));
  expect(pages).toHaveLength(2);
  for (const text of pages) expect(text.trim().length).toBeGreaterThan(100);
  await assertPrivate(context, page, observations);
});

for (const [label, location] of [["downloaded file", artifactURL], ["hosted page", "/"]]) {
  test(`${label}: checks applicant-supplied upload limits without rounding away excess bytes`, async ({ page, context }) => {
    const observations = await openReview(page, context, location);
    const buffer = pdfFixture([{ text: "First page" }, { text: "Second page" }]);
    await reviewFile(page, filePayload(buffer));
    await expect(page.locator('#upload-limits')).not.toHaveAttribute('open');
    await page.getByText('Application upload limits', { exact: true }).click();
    await expect(page.locator('#file-size')).toContainText(`${buffer.length.toLocaleString('en-US')} bytes`);
    await expect(page.locator('#page-limit-result')).toHaveText('No page limit set.');
    await expect(page.locator('#size-limit-result')).toHaveText('No file-size limit set.');
    await page.getByLabel('Maximum pages', { exact: true }).fill('1');
    await expect(page.locator('#page-limit-result')).toHaveText('2 pages; limit 1. Over the limit.');
    await page.getByLabel('Maximum pages', { exact: true }).fill('2');
    await expect(page.locator('#page-limit-result')).toContainText('Within the limit.');
    await page.getByLabel('Maximum file size (MB)', { exact: true }).fill((buffer.length / 1_000_000).toFixed(6));
    await expect(page.locator('#size-limit-result')).toContainText('Within the');
    await page.getByLabel('Maximum file size (MB)', { exact: true }).fill(((buffer.length - 1) / 1_000_000).toFixed(6));
    await expect(page.locator('#size-limit-result')).toContainText('by 1 byte.');
    // The check does not modify the extracted text, preview, or original file.
    await expect(page.locator('#all-text')).toHaveValue('First page\n\nSecond page');
    await expect(page.locator('#pages canvas')).toHaveCount(2);
    await assertPrivate(context, page, observations);
  });
}

test('upload limits reject invalid entries and allow either check to be removed', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture()));
  await page.getByText('Application upload limits', { exact: true }).click();
  await page.getByLabel('Maximum pages', { exact: true }).fill('1.5');
  await page.getByLabel('Maximum file size (MB)', { exact: true }).fill('-2');
  await expect(page.locator('#max-pages')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#max-mb')).toHaveAttribute('aria-invalid', 'true');
  await expect(page.locator('#page-limit-result')).toContainText('positive whole number');
  await expect(page.locator('#size-limit-result')).toContainText('positive MB value');
  await page.getByLabel('Maximum pages', { exact: true }).fill('');
  await page.getByLabel('Maximum file size (MB)', { exact: true }).fill('0.5');
  await expect(page.locator('#max-pages')).toHaveAttribute('aria-invalid', 'false');
  await expect(page.locator('#max-mb')).toHaveAttribute('aria-invalid', 'false');
  await expect(page.locator('#page-limit-result')).toHaveText('No page limit set.');
  await expect(page.locator('#size-limit-result')).toHaveText('Within the 0.5 MB limit.');
  await assertPrivate(context, page, observations);
});

test('upload limits recheck a replacement PDF and clear with the file', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: 'First' }, { text: 'Second' }])));
  await page.getByText('Application upload limits', { exact: true }).click();
  await page.getByLabel('Maximum pages', { exact: true }).fill('1');
  await page.getByLabel('Maximum file size (MB)', { exact: true }).fill('1');
  await expect(page.locator('#page-limit-result')).toContainText('Over the limit.');
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Shortened' }]), 'shortened.pdf'));
  await expect(page.locator('#max-pages')).toHaveValue('1');
  await expect(page.locator('#max-mb')).toHaveValue('1');
  await expect(page.locator('#page-limit-result')).toHaveText('Page count: 1. Limit: 1. Within the limit.');
  await page.getByRole('button', { name: 'Clear file', exact: true }).click();
  await expect(page.locator('#upload-limits')).toBeHidden();
  await expect(page.locator('#file-size')).toBeEmpty();
  await expect(page.locator('#max-pages')).toHaveValue('');
  await expect(page.locator('#max-mb')).toHaveValue('');
  await reviewFile(page, filePayload(pdfFixture()));
  await expect(page.locator('#upload-limits')).not.toHaveAttribute('open');
  await page.getByText('Application upload limits', { exact: true }).click();
  await expect(page.locator('#page-limit-result')).toHaveText('No page limit set.');
  await assertPrivate(context, page, observations);
});

test('an unreadable replacement clears upload-limit results', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture()));
  await page.getByText('Application upload limits', { exact: true }).click();
  await page.getByLabel('Maximum pages', { exact: true }).fill('1');
  await page.locator('#pdf-file').setInputFiles(filePayload(Buffer.from('%PDF-broken')));
  await expect(page.locator('#error')).toBeVisible();
  await expect(page.locator('#upload-limits')).toBeHidden();
  await expect(page.locator('#page-limit-result')).toBeEmpty();
  await expect(page.locator('#size-limit-result')).toBeEmpty();
  await assertPrivate(context, page, observations);
});

test('upload limits work by keyboard on a narrow screen', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.setViewportSize({ width: 320, height: 700 });
  await reviewFile(page, filePayload(pdfFixture()));
  const summary = page.getByText('Application upload limits', { exact: true });
  await summary.focus();
  await page.keyboard.press('Enter');
  await page.keyboard.press('Tab');
  await expect(page.locator('#max-pages')).toBeFocused();
  await page.keyboard.type('1');
  await page.keyboard.press('Tab');
  await expect(page.locator('#max-mb')).toBeFocused();
  await page.keyboard.type('0.5');
  await expect(page.locator('#size-limit-result')).toContainText('Within the');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await assertPrivate(context, page, observations);
});

test("distinguishes blank pages from image and vector pages without text", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([
    { text: "Readable resume text" },
    {},
    { image: true },
    { content: "0 0 0 rg 72 600 180 70 re f" },
  ])));
  await expect(page.locator(".page-card")).toHaveCount(4);
  const cards = page.locator(".page-card");
  await expect(cards.nth(1)).toContainText(/blank/i);
  for (const index of [2, 3]) {
    await expect(cards.nth(index)).toContainText(/no (extractable )?text/i);
    await expect(cards.nth(index).locator(".notice")).not.toContainText(/appears blank/i);
  }
  await expect(cards.nth(0).locator("textarea")).toHaveValue(/Readable resume text/);
  await assertPrivate(context, page, observations);
});

test("embedded CMaps extract Japanese text without a network request", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ cjk: true }])));
  await expect(page.locator("#all-text")).toHaveValue("日本語");
  await assertPrivate(context, page, observations);
});

test("embedded WebAssembly renders a JPEG2000 image without network access", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ jpeg2000: true }])));
  await expect(page.locator("#pages canvas")).toHaveCount(1);
  await expect(page.locator(".page-card .badge")).toContainText("No extractable text");
  await expect(page.locator("#summary")).not.toContainText("appear blank");
  const hasDarkPixels = await page.locator("#pages canvas").evaluate((canvas) => {
    const pixels = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
    return pixels.some((value, index) => index % 4 !== 3 && value < 50);
  });
  expect(hasDarkPixels).toBe(true);
  await assertPrivate(context, page, observations);
});

test("shows actual destinations without making PDF links executable", async ({ page, context }) => {
  const observations = await openReview(page, context);
  const links = [
    { label: "github.com/expected", url: "https://actual-destination.example/profile?from=resume#work" },
    { label: "Email", url: "mailto:person@example.test" },
    { label: "Phone", url: "tel:+15555550123" },
    { label: "Unsafe", url: "javascript:globalThis.pdfInjected=true" },
    { label: "Local file", url: "file:///private/should-not-open" },
    { label: "Page one", internal: true },
  ];
  await reviewFile(page, filePayload(pdfFixture([{ text: "Link destination checks", links }])));
  for (const link of links.filter((item) => item.url)) {
    await expect(page.locator("#pages")).toContainText(link.url);
  }
  await expect(page.locator("#pages")).toContainText(/internal|page destination/i);
  await expect(page.locator("#pages a[href]")).toHaveCount(0);
  const initialURL = page.url();
  for (const index of [3, 4, 5]) {
    await page.getByRole("button", { name: `Show link ${index + 1} on page 1`, exact: true }).click();
    await expect(page.locator(".link-overlay")).toBeVisible();
    await expect(page.locator(".preview-toolbar [role=status]")).toHaveText(`Link ${index + 1} · page 1`);
  }
  expect(page.url()).toBe(initialURL);
  expect(context.pages()).toHaveLength(1);
  expect(await page.evaluate(() => globalThis.pdfInjected)).toBeUndefined();
  await assertPrivate(context, page, observations);
});

for (const [rotation, expected] of [
  [0, { pageWidth: 612, pageHeight: 792, x: 72, y: 107, width: 228, height: 15 }],
  [90, { pageWidth: 792, pageHeight: 612, x: 670, y: 72, width: 15, height: 228 }],
  [180, { pageWidth: 612, pageHeight: 792, x: 312, y: 670, width: 228, height: 15 }],
  [270, { pageWidth: 792, pageHeight: 612, x: 107, y: 312, width: 15, height: 228 }],
]) {
  test(`link location matches the rendered ${rotation}-degree page and stays aligned at 390px`, async ({ page, context }) => {
    const observations = await openReview(page, context);
    await reviewFile(page, filePayload(pdfFixture([{
      rotation, text: "Rotated link position", links: [{ label: "Profile", url: "https://example.test/profile", rect: [72, 670, 300, 685] }],
    }])));
    const card = page.locator(".page-card");
    await expect(card.locator(".link-overlay")).toBeHidden();
    await page.getByRole("button", { name: "Show link 1 on page 1", exact: true }).click();
    await expect(card.locator(".link-overlay")).toBeVisible();
    await expect(card.locator(".link-highlight")).toHaveCount(1);
    await assertHighlightGeometry(card, expected);
    await page.setViewportSize({ width: 390, height: 844 });
    await assertHighlightGeometry(card, expected);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await assertPrivate(context, page, observations);
  });
}

test("same-line destinations have separate highlights and keyboard focus can return to the selected link", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: "Two links on the same line", links: [
    { label: "GitHub", url: "https://example.test/code", rect: [72, 670, 160, 685] },
    { label: "Portfolio", url: "https://example.test/work", rect: [220, 670, 320, 685] },
  ] }])));
  const first = page.getByRole("button", { name: "Show link 1 on page 1", exact: true });
  const second = page.getByRole("button", { name: "Show link 2 on page 1", exact: true });
  const card = page.locator(".page-card");
  const rows = card.locator(".link-list li");
  await first.focus();
  await page.keyboard.press("Enter");
  await expect(first).toBeFocused();
  await expect(first).toHaveAttribute("aria-pressed", "true");
  await expect(rows.nth(0)).toHaveClass("is-selected");
  await assertHighlightGeometry(card, { pageWidth: 612, pageHeight: 792, x: 72, y: 107, width: 88, height: 15 });
  await second.focus();
  await page.keyboard.press("Space");
  await expect(first).toHaveAttribute("aria-pressed", "false");
  await expect(second).toHaveAttribute("aria-pressed", "true");
  await expect(rows.nth(0)).not.toHaveClass("is-selected");
  await expect(rows.nth(1)).toHaveClass("is-selected");
  await expect(card.locator(".preview-toolbar [role=status]")).toHaveText("Link 2 · page 1");
  await assertHighlightGeometry(card, { pageWidth: 612, pageHeight: 792, x: 220, y: 107, width: 100, height: 15 });
  await page.setViewportSize({ width: 390, height: 844 });
  await card.getByRole("button", { name: "Back to link" }).click();
  await expect(second).toBeFocused();
  await expect(second).toBeInViewport();
  await page.keyboard.press("Enter");
  await expect(second).toHaveAttribute("aria-pressed", "false");
  await expect(card.locator(".link-overlay")).toBeHidden();
  await expect(card.locator("li.is-selected")).toHaveCount(0);
  await expect(card.locator(".preview-toolbar [role=status]")).toHaveText("PDF page");
  await expect(card.getByRole("button", { name: "Back to link" })).toBeHidden();
  await assertPrivate(context, page, observations);
});

test("enlarging a narrow preview keeps the selected link visible and Fit page restores its size", async ({ page, context }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: "Inspect a lower-right link", links: [
    { label: "Portfolio", url: "https://example.test/lower-right", rect: [480, 100, 550, 115] },
  ] }])));
  const card = page.locator(".page-card");
  const expected = { pageWidth: 612, pageHeight: 792, x: 480, y: 677, width: 70, height: 15 };
  const originalWidth = (await card.locator("canvas").boundingBox()).width;
  await card.locator(".locate-link").click();
  await card.locator(".enlarge-preview").click();
  await expect(card.locator(".enlarge-preview")).toHaveAttribute("aria-pressed", "true");
  await expect(card.locator(".enlarge-preview")).toHaveAccessibleName("Fit page 1 preview");
  await expect(card.locator(".enlarge-preview")).toHaveText("Fit page");
  await expect(card.locator(".preview-viewport")).toHaveAttribute("tabindex", "0");
  expect((await card.locator("canvas").boundingBox()).width).toBeGreaterThan(originalWidth * 2);
  await assertHighlightGeometry(card, expected);
  const scrolling = await card.locator(".preview-viewport").evaluate((viewport) => {
    const visible = viewport.getBoundingClientRect();
    const selected = viewport.querySelector(".link-highlight").getBoundingClientRect();
    return {
      x: viewport.scrollLeft, y: viewport.scrollTop,
      contained: selected.left >= visible.left && selected.right <= visible.right
        && selected.top >= visible.top && selected.bottom <= visible.bottom,
    };
  });
  expect(scrolling.x).toBeGreaterThan(0);
  expect(scrolling.y).toBeGreaterThan(0);
  expect(scrolling.contained).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await card.locator(".preview-viewport").focus();
  await page.keyboard.press("ArrowLeft");
  await expect.poll(() => card.locator(".preview-viewport").evaluate((viewport) => viewport.scrollLeft)).toBeLessThan(scrolling.x);
  const scrolledLeft = await card.locator(".preview-viewport").evaluate((viewport) => viewport.scrollLeft);
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => card.locator(".preview-viewport").evaluate((viewport) => viewport.scrollLeft)).toBeGreaterThan(scrolledLeft);
  await card.locator(".enlarge-preview").click();
  await expect(card.locator(".enlarge-preview")).toHaveAttribute("aria-pressed", "false");
  await expect(card.locator(".enlarge-preview")).toHaveAccessibleName("Enlarge page 1 preview");
  await expect(card.locator(".enlarge-preview")).toHaveText("Enlarge");
  await expect(card.locator(".preview-viewport")).toHaveAttribute("tabindex", "-1");
  expect((await card.locator("canvas").boundingBox()).width).toBeCloseTo(originalWidth, 0);
  await expect(card.locator(".locate-link")).toHaveAttribute("aria-pressed", "true");
  await assertHighlightGeometry(card, expected);
  await assertPrivate(context, page, observations);
});

test("invalid and off-page rectangles and failed previews explain unavailable link positions", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([
    { text: "Invalid link geometry", links: [
      { url: "https://example.test/zero-area", rect: [72, 670, 72, 685] },
      { url: "https://example.test/off-page", rect: [700, 670, 800, 685] },
      { url: "https://example.test/incomplete", rect: [72, 670, 100] },
    ] },
    { text: "Preview cannot be rendered", mediaBox: "0 0 20000 20000", links: [{ url: "https://example.test/large-page" }] },
  ])));
  await expect(page.locator(".locate-link")).toHaveCount(4);
  for (const button of await page.locator(".locate-link").all()) await expect(button).toBeDisabled();
  for (const note of await page.locator(".page-card").first().locator(".position-note").all()) {
    await expect(note).toBeVisible();
    await expect(note).toHaveText("Position unavailable in this preview.");
  }
  await expect(page.locator(".page-card").nth(1).locator(".position-note")).toHaveText("Position unavailable without a preview.");
  await expect(page.locator(".page-card").nth(1).locator("canvas")).toHaveCount(0);
  await expect(page.locator(".link-overlay:not([hidden])")).toHaveCount(0);
  await assertPrivate(context, page, observations);
});

test("clearing and replacing a review remove its selected link and highlight", async ({ page, context }) => {
  const observations = await openReview(page, context);
  const payload = filePayload(pdfFixture([{ text: "Selected review", links: [{ url: "https://example.test/old" }] }]), "selected.pdf");
  await reviewFile(page, payload);
  await page.locator(".locate-link").click();
  await expect(page.locator(".link-overlay")).toBeVisible();
  await reviewFile(page, filePayload(pdfFixture([{ text: "Replacement review", links: [{ url: "https://example.test/new" }] }]), "replacement.pdf"));
  await expect(page.locator(".link-overlay")).toBeHidden();
  await expect(page.locator(".locate-link")).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("li.is-selected")).toHaveCount(0);
  await expect(page.locator("#pages")).not.toContainText("https://example.test/old");
  await page.locator(".locate-link").click();
  await page.locator("#clear-file").click();
  await expect(page.locator(".link-highlight")).toHaveCount(0);
  await expect(page.locator("#pages")).toBeEmpty();
  await expect(page.locator("#pdf-file")).toBeFocused();
  await reviewFile(page, payload);
  await expect(page.locator(".link-overlay")).toBeHidden();
  await expect(page.locator(".locate-link")).toHaveAttribute("aria-pressed", "false");
  await assertPrivate(context, page, observations);
});

test("the desktop review puts the preview and copy action within the first screen", async ({ page, context }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: "Compact resume review" }])));
  await expect(page.locator("#empty-state")).toBeHidden();
  await expect(page.locator(".all-text-panel")).not.toHaveAttribute("open");
  await expect(page.locator("#copy-all")).toBeInViewport();
  const canvas = await page.locator("#pages canvas").boundingBox();
  const extracted = await page.locator(".page-card textarea").boundingBox();
  expect(canvas.y).toBeLessThan(450);
  expect(canvas.y + canvas.height / 2).toBeLessThan(900);
  expect(extracted.x).toBeGreaterThan(canvas.x + canvas.width);
  expect(Math.abs(extracted.y - canvas.y)).toBeLessThan(30);
  await assertPrivate(context, page, observations);
});

test("the keyboard file picker has a visible focus indicator and Help opens its explanation", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.locator(".site-name").focus();
  await page.keyboard.press("Tab");
  // Safari can use the macOS Option+Tab setting for buttons and file inputs;
  // other platforms reach them with Tab, so try their native behavior first.
  if (context.browser().browserType().name() === "webkit" && !await page.locator("#pdf-file").evaluate((input) => input === document.activeElement)) {
    await page.locator(".site-name").focus();
    await page.keyboard.press("Alt+Tab");
  }
  await expect(page.locator("#pdf-file")).toBeFocused();
  const outline = await page.locator('label[for="pdf-file"]').evaluate((label) => {
    const style = getComputedStyle(label);
    return { style: style.outlineStyle, width: parseFloat(style.outlineWidth) };
  });
  expect(outline.style).toBe("solid");
  expect(outline.width).toBeGreaterThanOrEqual(2);
  const chooserPromise = page.waitForEvent("filechooser");
  await page.keyboard.press("Space");
  const chooser = await chooserPromise;
  await chooser.setFiles(filePayload(pdfFixture([{ text: "Chosen with the keyboard" }])));
  await expect(page.locator("#status")).toHaveText("Review ready.");
  await expect(page.locator("#all-text")).toHaveValue("Chosen with the keyboard");
  await expect(page.locator("#review-help")).not.toHaveAttribute("open");
  await page.locator(".help-link").click();
  await expect(page.locator("#review-help")).toHaveAttribute("open", "");
  await expect(page.locator("#review-help > div")).toBeVisible();
  await assertPrivate(context, page, observations);
});

test("renders PDF strings and filenames as text, never markup", async ({ page, context }) => {
  const observations = await openReview(page, context);
  const injection = '<img src="https://example.invalid/leak" onerror="globalThis.pdfInjected=true">';
  await reviewFile(page, filePayload(pdfFixture([{ text: injection }], { title: injection }), "<svg onload=alert(1)>.pdf"));
  await expect(page.locator("#all-text")).toHaveValue(injection);
  await expect(page.locator("#filename")).toHaveText("<svg onload=alert(1)>.pdf");
  await expect(page.locator("#review img, #filename svg")).toHaveCount(0);
  expect(await page.evaluate(() => globalThis.pdfInjected)).toBeUndefined();
  await assertPrivate(context, page, observations);
});

test("warns about form values that page-text extraction may omit", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: "Form resume", formValue: "Stored form value" }])));
  await expect(page.locator("#review")).toContainText(/form/i);
  // PDF form widgets must not become active inputs. The only review inputs
  // belong to our optional upload-limit controls, not the document.
  await expect(page.locator("#pages input, #pages form")).toHaveCount(0);
  await expect(page.locator("#review input")).toHaveCount(2);
  await assertPrivate(context, page, observations);
});

test("password retry and cancellation stay local and recover", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.locator("#pdf-file").setInputFiles(filePayload(encryptedFixture()));
  await expect(page.locator("#password-form")).toBeVisible();
  await page.locator("#password").fill("incorrect");
  await page.locator("#password-form button[type=submit]").click();
  await expect(page.locator("#password-form")).toBeVisible();
  await page.locator("#password").fill("review-test");
  await page.locator("#password-form button[type=submit]").click();
  await expect(page.locator("#status")).toHaveText("Review ready.");
  await expect(page.locator("#all-text")).toHaveValue(/Protected resume fixture/);
  await expect(page.locator("#password")).toHaveValue("");
  await page.locator("#pdf-file").setInputFiles(filePayload(encryptedFixture(), "locked-again.pdf"));
  await expect(page.locator("#password-form")).toBeVisible();
  await page.locator("#cancel-password").click();
  await expect(page.locator("#password-form")).toBeHidden();
  await expect(page.locator("#review")).toBeHidden();
  await reviewFile(page, filePayload(pdfFixture([{ text: "Recovered after password cancellation" }])));
  await assertPrivate(context, page, observations);
});

test("rejects malformed, empty, oversized, and excessive-page inputs and recovers", async ({ page, context }) => {
  const observations = await openReview(page, context);
  for (const [name, buffer] of [
    ["not-a-pdf.pdf", Buffer.from("This is plain text, not a PDF.")],
    ["broken.pdf", Buffer.from("%PDF-1.7\nnot a valid document")],
    ["empty.pdf", Buffer.alloc(0)],
    ["oversized.pdf", Buffer.alloc(20 * 1024 * 1024 + 1)],
    ["too-many-pages.pdf", pdfFixture(Array.from({ length: 21 }, () => ({})))],
  ]) {
    await page.locator("#pdf-file").setInputFiles(filePayload(buffer, name));
    await expect(page.locator("#error"), name).toBeVisible();
    await expect(page.locator("#error"), name).not.toHaveText("");
    await expect(page.locator("#review"), name).toBeHidden();
  }
  await reviewFile(page, filePayload(pdfFixture([{ text: "A valid PDF after failures" }])));
  await assertPrivate(context, page, observations);
});

test("clears all extracted data and can select the same file again", async ({ page, context }) => {
  const observations = await openReview(page, context);
  const payload = filePayload(pdfFixture([{ text: "Data that must be discarded" }]));
  await reviewFile(page, payload);
  await page.locator("#clear-file").click();
  await expect(page.locator("#review")).toBeHidden();
  await expect(page.locator("#pages")).toBeEmpty();
  await expect(page.locator("#all-text")).toHaveValue("");
  await expect(page.locator("#filename")).toHaveText("");
  await expect(page.locator("#pdf-file")).toHaveValue("");
  await reviewFile(page, payload);
  await assertPrivate(context, page, observations);
});

test("accepts a dropped PDF based on its contents, not its filename", async ({ page, context }) => {
  const observations = await openReview(page, context);
  const bytes = [...pdfFixture([{ text: "PDF dropped without a PDF extension" }])];
  await page.locator("#drop-zone").evaluate((zone, data) => {
    const transfer = new DataTransfer();
    transfer.items.add(new File([new Uint8Array(data)], "resume-export", { type: "application/octet-stream" }));
    zone.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: transfer }));
  }, bytes);
  await expect(page.locator("#status")).toHaveText("Review ready.");
  await expect(page.locator("#all-text")).toHaveValue("PDF dropped without a PDF extension");
  await assertPrivate(context, page, observations);
});

test("an unsupported page size is not reported as blank", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: "Oversized page", mediaBox: "0 0 20000 20000" }])));
  await expect(page.locator(".page-card")).toContainText(/preview unavailable|manual review/i);
  await expect(page.locator("#summary")).not.toContainText("appear blank");
  await expect(page.locator("#pages canvas")).toHaveCount(0);
  await assertPrivate(context, page, observations);
});

test("clearing during processing cannot restore the discarded review", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.locator("#pdf-file").setInputFiles(filePayload(pdfFixture(Array.from({ length: 20 }, () => ({ text: "Clear this unfinished review" })))));
  await page.locator("#clear-file").click();
  await expect(page.locator("#status")).toHaveText("Review cleared.");
  await expect(page.locator("#review")).toBeHidden();
  await expect(page.locator("#pages")).toBeEmpty();
  await reviewFile(page, filePayload(pdfFixture([{ text: "Fresh review after cancellation" }])));
  await expect(page.locator("#all-text")).toHaveValue("Fresh review after cancellation");
  await expect(page.locator(".page-card")).toHaveCount(1);
  await assertPrivate(context, page, observations);
});

test("a replacement file cannot receive stale results from the previous review", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.locator("#pdf-file").setInputFiles(filePayload(pdfFixture(Array.from({ length: 20 }, () => ({ text: "Old document content" }))), "old.pdf"));
  await page.locator("#pdf-file").setInputFiles(filePayload(pdfFixture([{ text: "Only the replacement belongs here" }]), "replacement.pdf"));
  await expect(page.locator("#status")).toHaveText("Review ready.");
  await expect(page.locator("#filename")).toHaveText("replacement.pdf");
  await expect(page.locator(".page-card")).toHaveCount(1);
  await expect(page.locator("#all-text")).toHaveValue("Only the replacement belongs here");
  await expect(page.locator("#review")).not.toContainText("Old document content");
  await assertPrivate(context, page, observations);
});

test("clipboard failure still leaves all text available for manual copying", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: async () => { throw new DOMException("Permission denied", "NotAllowedError"); } },
    });
    document.execCommand = () => false;
  });
  await reviewFile(page, filePayload(pdfFixture([{ text: "Copy this text manually" }])));
  await expect(page.locator(".all-text-panel")).not.toHaveAttribute("open");
  await expect(page.locator("#copy-all")).toBeVisible();
  await page.locator("#copy-all").click();
  await expect(page.locator("#all-text")).toBeVisible();
  await expect(page.locator("#all-text")).toBeFocused();
  await expect(page.locator("#all-text")).toHaveValue("Copy this text manually");
  await expect(page.locator("#status")).toContainText(/select|copy|clipboard/i);
  await assertPrivate(context, page, observations);
});

test("copy buttons send only extracted text to the clipboard", async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.evaluate(() => {
    globalThis.copiedValues = [];
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: async (value) => globalThis.copiedValues.push(value) },
    });
  });
  await reviewFile(page, filePayload(pdfFixture([{ text: "First page content" }, { text: "Second page content" }])));
  const pageCopy = page.locator(".page-card").first().getByRole("button", { name: "Copy page text" });
  await pageCopy.click();
  await expect(page.locator(".page-card").first().getByRole("button", { name: "Copied", exact: true })).toBeVisible();
  await expect(page.locator(".all-text-panel")).not.toHaveAttribute("open");
  await page.locator("#copy-all").click();
  await expect(page.locator("#copy-all")).toHaveText("Copied");
  await expect(page.locator("#status")).toContainText("Text copied.");
  expect(await page.evaluate(() => globalThis.copiedValues)).toEqual([
    "First page content", "First page content\n\nSecond page content",
  ]);
  await page.locator("#clear-file").click();
  await expect(page.locator("#copy-all")).toHaveText("Copy all text");
  await expect(page.locator("#copy-all")).toBeDisabled();
  await expect(page.locator("#all-text")).toHaveValue("");
  await expect(page.locator("#status")).toHaveText("Review cleared.");
  await assertPrivate(context, page, observations);
});

for (const [label, location] of [["downloaded file", artifactURL], ["hosted page", "/"]]) {
  test(`${label}: edits and saves a text copy without changing the PDF extraction`, async ({ page, context }) => {
    const observations = await openReview(page, context, location);
    await reviewFile(page, filePayload(pdfFixture([{ text: 'Original first page' }, { text: 'Original second page' }]), 'My Resume.PDF'));
    await page.locator('.all-text-panel > summary').click();
    const draft = page.locator('#all-text');
    const original = await draft.inputValue();
    const edited = 'Zoë — 研究\n\n• Tested retries.\n<not HTML>\n';
    await expect(draft).toBeEditable();
    await expect(page.locator('#reset-text')).toBeDisabled();
    await draft.fill(edited);
    await expect(page.locator('.page-card textarea').first()).toHaveValue('Original first page');
    await expect(page.locator('.page-card textarea').first()).toHaveAttribute('readonly', '');
    const pending = page.waitForEvent('download');
    await page.locator('#save-text').click();
    const download = await pending;
    expect(download.suggestedFilename()).toBe('My Resume-text.txt');
    const chunks = [];
    for await (const chunk of await download.createReadStream()) chunks.push(chunk);
    expect(Buffer.concat(chunks).toString('utf8')).toBe(edited);
    expect(await download.failure()).toBeNull();
    await page.locator('#reset-text').click();
    await expect(draft).toHaveValue(original);
    await expect(page.locator('#reset-text')).toBeDisabled();
    await assertPrivate(context, page, observations);
  });
}

test('copy all uses the edited draft while copy page retains the PDF text', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await page.evaluate(() => {
    globalThis.copiedValues = [];
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true, value: { writeText: async value => globalThis.copiedValues.push(value) },
    });
  });
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Original PDF text' }])));
  await page.locator('.all-text-panel > summary').click();
  await page.locator('#all-text').fill('Edited text for the form');
  await page.locator('#copy-all').click();
  await page.getByRole('button', { name: 'Copy page text' }).click();
  expect(await page.evaluate(() => globalThis.copiedValues)).toEqual(['Edited text for the form', 'Original PDF text']);
  await assertPrivate(context, page, observations);
});

test('empty drafts disable copy and save but can be reset', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Recover this extraction' }])));
  await page.locator('.all-text-panel > summary').click();
  await page.locator('#all-text').fill(' \n ');
  await expect(page.locator('#copy-all')).toBeDisabled();
  await expect(page.locator('#save-text')).toBeDisabled();
  await expect(page.locator('#reset-text')).toBeEnabled();
  await page.locator('#reset-text').click();
  await expect(page.locator('#all-text')).toHaveValue('Recover this extraction');
  await assertPrivate(context, page, observations);
});

test('text edits are discarded on replacement, clearing, and reload', async ({ page, context }) => {
  const observations = await openReview(page, context, artifactURL);
  await reviewFile(page, filePayload(pdfFixture([{ text: 'First document' }])));
  await page.locator('.all-text-panel > summary').click();
  await page.locator('#all-text').fill('Private edited draft');
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Replacement document' }])));
  await expect(page.locator('#all-text')).toHaveValue('Replacement document');
  await page.locator('.all-text-panel > summary').click();
  await page.locator('#all-text').fill('Another draft');
  await page.locator('#clear-file').click();
  await expect(page.locator('#all-text')).toHaveValue('');
  await expect(page.locator('#all-text')).toHaveAttribute('readonly', '');
  await expect(page.locator('#save-text')).toBeDisabled();
  await expect(page.locator('#reset-text')).toBeDisabled();
  await page.reload();
  await expect(page.locator('#all-text')).toHaveValue('');
  await expect(page.locator('#review')).toBeHidden();
  await assertPrivate(context, page, observations);
});

test('incomplete text stays visible beside the editable copy', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Readable page' }, { image: true }])));
  await page.locator('.all-text-panel > summary').click();
  await expect(page.locator('#draft-warning')).toBeVisible();
  await expect(page.locator('#draft-warning')).toContainText('Some PDF text was not extracted');
  await page.locator('#all-text').fill('A manual text copy');
  await expect(page.locator('#draft-warning')).toBeVisible();
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Complete extraction' }])));
  await page.locator('.all-text-panel > summary').click();
  await expect(page.locator('#draft-warning')).toBeHidden();
  await assertPrivate(context, page, observations);
});

test('a download failure preserves edits and offers copying', async ({ page, context }) => {
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: 'Keep this text' }])));
  await page.locator('.all-text-panel > summary').click();
  await page.locator('#all-text').fill('Unsaved edits');
  await page.evaluate(() => { URL.createObjectURL = () => { throw new Error('Download unavailable'); }; });
  await page.locator('#save-text').click();
  await expect(page.locator('#status')).toContainText('Use Copy all text instead');
  await expect(page.locator('#all-text')).toHaveValue('Unsaved edits');
  await expect(page.locator('#copy-all')).toBeEnabled();
  await assertPrivate(context, page, observations);
});

test("remains usable at a narrow viewport", async ({ page, context }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const observations = await openReview(page, context);
  await reviewFile(page, filePayload(pdfFixture([{ text: "Small-screen resume review", links: [{ url: `https://example.test/${"long-path-".repeat(35)}` }] }])));
  const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  expect(fits).toBe(true);
  await expect(page.locator("#clear-file")).toBeVisible();
  await expect(page.locator(".page-card textarea")).toBeVisible();
  await page.locator('.all-text-panel > summary').click();
  await expect(page.locator('#save-text')).toBeVisible();
  await expect(page.locator('#all-text')).toBeEditable();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await assertPrivate(context, page, observations);
});
