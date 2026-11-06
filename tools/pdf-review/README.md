# PDF review

Read a resume PDF beside its extracted text and inspect its links.

## Use it

1. [Download the reviewer](https://raw.githubusercontent.com/deepdave98/latex-resume-and-cv-templates/main/downloads/pdf-review.zip), unzip it, and open `pdf-review.html` in a current browser.
2. Choose **Open PDF** or drop one file onto the file bar.
3. Read each page beside its text; **Show on page** locates a link.
4. Open **Text for application forms** and choose **Copy all text**.

One PDF at a time, up to **20 MiB and 20 pages**, offline. Protected files ask for their password locally.

## What to check

- **Text:** compare names, symbols, and reading order with the PDF. Ligatures such as `ﬁ` become plain letters. Scans need a text layer; there is no OCR or ATS test. Counts include spaces and line breaks.
- **Links:** compare each destination with its printed label; **Enlarge** helps with small labels. Links stay inert: test them in a PDF reader.
- **Blank pages:** preview hints can miss faint content; a failed preview is never called blank.
- **Paper size:** check dimensions and orientation against the application; cropping, rotation, and scale are included.
- **Sample contacts:** flagged starter email, phone, or profile links need replacing; only known samples are caught.

## Privacy

PDFs, passwords, text, and links stay in browser memory. Nothing is uploaded, stored, or downloaded; there are no analytics, cookies, or service workers. PDF links and scripts never run, and the security policy blocks network connections. Clearing, reloading, or closing discards the review. It cannot wipe memory or control extensions. A host sees the page request, not the PDF. Copied text may remain in clipboard history.

## Development

Node.js 22.13+:

```bash
cd tools/pdf-review
npm ci --ignore-scripts
npm run build
npm test
npx playwright install --with-deps chromium firefox webkit
npm run test:browser
npm run check
```

`build` writes the HTML and a reproducible ZIP to `downloads/`. Commit the ZIP only; `check` fails if it is stale. Browser tests run offline in Chromium, Firefox, and WebKit and assert no post-load requests or storage. Preview locally with `node server.mjs` at `http://127.0.0.1:4178/`.

| File | Purpose |
| --- | --- |
| `index.html`, `styles.css` | Interface |
| `src/app.mjs` | Lifecycle, worker, previews, DOM |
| `src/review.mjs` | Text and annotation inspection |
| `src/link-region.mjs` | Link bounds on the rendered page |
| `src/page-size.mjs`, `src/file-size.mjs` | Paper size and file size labels |
| `build.mjs` | PDF.js assets, CSP hashes, ZIP |
| `tests/` | Unit, package, browser checks |

PDF.js is pinned in `package-lock.json`; update it through a dependency PR, rebuild the ZIP, and run all checks. Its licenses appear in the page under **PDF engine and licenses**.

The HTML works on a static host without a backend or third-party scripts. Enable **Settings → Pages → Source: GitHub Actions** and run **Publish PDF review** on `main`; downloaded copies do not update themselves.
