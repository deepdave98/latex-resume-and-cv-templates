// The shipped page needs no server, CDN, package manager, or network access.
import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { zipSync } from 'fflate';

const root = path.dirname(fileURLToPath(import.meta.url));
const pdfRoot = path.join(root, 'node_modules/pdfjs-dist');
const output = path.resolve(root, '../../downloads/pdf-review.html');
const archive = path.resolve(root, '../../downloads/pdf-review.zip');
const readText = async filename => (await readFile(filename, 'utf8')).replace(/\r\n?/g, '\n');
const assets = {};
const licenses = [];
for (const [kind, directory, extensions] of [
  ['cMapUrl', 'cmaps', ['.bcmap']],
  ['standardFontDataUrl', 'standard_fonts', ['.pfb', '.ttf']],
  ['wasmUrl', 'wasm', ['.wasm']],
]) {
  assets[kind] = {};
  for (const name of (await readdir(path.join(pdfRoot, directory))).sort()) {
    if (name.startsWith('LICENSE')) {
      licenses.push(`${directory}/${name}\n${await readText(path.join(pdfRoot, directory, name))}`);
    } else if (extensions.includes(path.extname(name))) {
      // PDF scripting is not used. Include only image decoding binaries.
      if (kind === 'wasmUrl' && !['jbig2.wasm', 'openjpeg.wasm'].includes(name)) continue;
      assets[kind][name] = (await readFile(path.join(pdfRoot, directory, name))).toString('base64');
    }
  }
}
licenses.unshift(`PDF.js\n${await readText(path.join(pdfRoot, 'LICENSE'))}`);
licenses.unshift(`Private PDF review\n${await readText(path.resolve(root, '../../LICENSE'))}`);
// Classic blob workers work on opaque file:// origins too. The PDF.js worker
// initializes its message handler on the worker global; no exports are needed.
const workerBundle = await build({
  entryPoints: [path.join(pdfRoot, 'legacy/build/pdf.worker.mjs')],
  bundle: true, write: false, format: 'iife', minify: true,
  target: ['chrome125', 'firefox128', 'safari18'], legalComments: 'inline',
});
const worker = workerBundle.outputFiles[0].text + '\nself.postMessage({resumeReviewWorkerReady:true});';
const bundle = await build({
  absWorkingDir: root,
  entryPoints: ['src/app.mjs'],
  bundle: true,
  write: false,
  format: 'iife',
  target: ['chrome125', 'firefox128', 'safari18'],
  minify: true,
  legalComments: 'inline',
  define: {
    __PDF_ASSETS__: JSON.stringify(assets),
    __WORKER_SOURCE__: JSON.stringify(worker),
    __THIRD_PARTY_LICENSES__: JSON.stringify(licenses.join('\n\n--------------------\n\n')),
  },
});
const script = bundle.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const css = await readText(path.join(root, 'styles.css'));
const hash = text => createHash('sha256').update(text).digest('base64');
const csp = `default-src 'none'; script-src 'sha256-${hash(script)}' 'wasm-unsafe-eval'; worker-src blob:; child-src blob:; style-src 'sha256-${hash(css)}'; img-src data: blob:; font-src data: blob:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'`;
const html = (await readText(path.join(root, 'index.html')))
  .replace('<!-- APP_CSP -->', () => `<meta http-equiv="Content-Security-Policy" content="${csp}">`)
  .replace('<link rel="stylesheet" href="styles.css">', () => `<style>${css}</style>`)
  .replace('<!-- APP_SCRIPT -->', () => `<script>${script}</script>`);
// The ZIP is the public download; HTML is a generated local/hosting artifact.
// Fixed metadata keeps the archive identical across machines and rebuilds.
const zipped = zipSync({ 'pdf-review.html': new TextEncoder().encode(html) }, {
  level: 9, mtime: new Date(2020, 0, 1, 0, 0, 0), os: 3, attrs: 0o100644 << 16,
});
if (process.argv.includes('--check')) {
  const existing = await readFile(archive).catch(() => Buffer.alloc(0));
  if (!existing.equals(Buffer.from(zipped))) {
    console.error('The downloadable review page is stale. Run npm run build in tools/pdf-review.');
    process.exitCode = 1;
  } else console.log('PASS: downloadable review page matches its source.');
} else {
  const staging = await mkdtemp(path.join(path.dirname(output), '.pdf-review-build-'));
  try {
    const stagedHTML = path.join(staging, 'pdf-review.html');
    const stagedZIP = path.join(staging, 'pdf-review.zip');
    await writeFile(stagedHTML, html);
    await writeFile(stagedZIP, zipped);
    await rename(stagedZIP, archive);
    await rename(stagedHTML, output);
  } finally {
    await rm(staging, { recursive: true, force: true });
  }
  console.log(`Built downloads/pdf-review.html (${(Buffer.byteLength(html) / 1024 / 1024).toFixed(1)} MB).`);
  console.log(`Built downloads/pdf-review.zip (${(zipped.length / 1024 / 1024).toFixed(1)} MB).`);
}
