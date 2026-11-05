import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { unzipSync } from 'fflate';
import { createSubmissionArchive, SubmissionArchiveError } from '../src/submission-archive.mjs';

const pdf = new TextEncoder().encode('%PDF-1.7\nOriginal PDF bytes\n%%EOF\n');
const date = new Date(2026, 10, 5, 12, 34, 56);

async function contents(result) {
  const files = unzipSync(new Uint8Array(await result.blob.arrayBuffer()));
  const folder = result.filename.slice(0, -4);
  const receipt = JSON.parse(new TextDecoder().decode(files[`${folder}/receipt.json`]));
  return { files, folder, receipt };
}

test('submission ZIP contains only the selected PDF and its compatible receipt', async () => {
  const result = await createSubmissionArchive(pdf, '  Acme - Backend Engineer  ', date);
  assert.equal(result.filename, '2026-11-05-acme-backend-engineer.zip');
  assert.equal(result.blob.type, 'application/zip');
  const { files, folder, receipt } = await contents(result);
  assert.deepEqual(Object.keys(files), [`${folder}/resume-acme-backend-engineer.pdf`, `${folder}/receipt.json`]);
  assert.deepEqual(files[`${folder}/${receipt.pdf}`], pdf);
  assert.deepEqual(Object.keys(receipt), ['label', 'saved_at', 'pdf', 'bytes', 'sha256']);
  assert.equal(receipt.label, 'Acme - Backend Engineer');
  assert.equal(receipt.bytes, pdf.length);
  assert.equal(receipt.sha256, createHash('sha256').update(pdf).digest('hex'));
  assert.equal(new Date(receipt.saved_at).getTime(), date.getTime());
  assert.equal(new TextDecoder().decode(files[`${folder}/receipt.json`]).includes('Original PDF bytes'), false);
});

test('hash and PDF use one private snapshot, including a view into a larger buffer', async () => {
  const source = new Uint8Array(pdf.length + 10).fill(255);
  source.set(pdf, 4);
  const view = source.subarray(4, 4 + pdf.length);
  const pending = createSubmissionArchive(view, 'Acme', date);
  source.fill(0);
  const { files, folder, receipt } = await contents(await pending);
  assert.deepEqual(files[`${folder}/${receipt.pdf}`], pdf);
  assert.equal(receipt.sha256, createHash('sha256').update(pdf).digest('hex'));
});

test('labels form portable names while the receipt retains the supplied label', async () => {
  for (const [label, slug] of [
    ['../../Acme\\Platform', 'acme-platform'],
    ['Québec / 软件 42', 'québec-软件-42'],
    ['İstanbul', 'i-stanbul'],
    ['CON', 'con'],
    ['a'.repeat(100), 'a'.repeat(80)],
    ['\u{20000}'.repeat(100), '\u{20000}'.repeat(50)],
  ]) {
    const result = await createSubmissionArchive(pdf, label, date);
    const { files, folder, receipt } = await contents(result);
    assert.equal(result.filename, `2026-11-05-${slug}.zip`);
    assert.equal(receipt.label, label);
    assert.equal(receipt.pdf, `resume-${slug}.pdf`);
    assert.ok(new TextEncoder().encode(receipt.pdf).length <= 255);
    assert.ok(new TextEncoder().encode(folder).length <= 255);
    assert.ok(new TextEncoder().encode(result.filename).length <= 255);
    assert.deepEqual(files[`${folder}/${receipt.pdf}`], pdf);
  }
});

test('local date and UTC offset agree at a date boundary and fractional-hour offset', () => {
  const moduleURL = new URL('../src/submission-archive.mjs', import.meta.url).href;
  const script = `
    import { unzipSync } from 'fflate';
    import { createSubmissionArchive } from ${JSON.stringify(moduleURL)};
    const result = await createSubmissionArchive(new TextEncoder().encode('%PDF-1.7\\n'), 'Acme', new Date('2026-11-05T02:03:04.500Z'));
    const files = unzipSync(new Uint8Array(await result.blob.arrayBuffer()));
    const receipt = JSON.parse(new TextDecoder().decode(files[result.filename.slice(0, -4) + '/receipt.json']));
    console.log(JSON.stringify({ filename: result.filename, saved_at: receipt.saved_at }));
  `;
  for (const [zone, timestamp] of [
    ['America/Toronto', '2026-11-04T21:03:04-05:00'],
    ['Asia/Kathmandu', '2026-11-05T07:48:04+05:45'],
    ['UTC', '2026-11-05T02:03:04+00:00'],
  ]) {
    const actual = JSON.parse(execFileSync(process.execPath, ['--input-type=module', '-e', script], {
      cwd: new URL('../', import.meta.url), env: { ...process.env, TZ: zone }, encoding: 'utf8', timeout: 10_000,
    }));
    assert.deepEqual(actual, { filename: `${timestamp.slice(0, 10)}-acme.zip`, saved_at: timestamp });
  }
});

test('the opened PDF is preserved even when its header follows a preamble', async () => {
  const original = new TextEncoder().encode('Preamble\r\n%PDF-1.7\nOriginal content\n%%EOF');
  const { files, folder, receipt } = await contents(await createSubmissionArchive(original, 'Acme', date));
  assert.deepEqual(files[`${folder}/${receipt.pdf}`], original);
  assert.equal(receipt.sha256, createHash('sha256').update(original).digest('hex'));
});

test('invalid labels, dates, and missing bytes cannot produce an archive', async () => {
  for (const label of ['', '   ', '../--', 'Acme\nRole', 'Acme\t', 'Acme\u200b', 'Acme\u00a0', '\ud800', null, {}]) {
    await assert.rejects(createSubmissionArchive(pdf, label, date), error => error instanceof SubmissionArchiveError && /label/u.test(error.message));
  }
  for (const savedAt of [new Date(NaN), new Date('0000-01-01T00:00:00Z'), new Date('+020000-01-01T00:00:00Z'), 'today', null]) {
    await assert.rejects(createSubmissionArchive(pdf, 'Acme', savedAt), /date/u);
  }
  for (const bytes of [new Uint8Array(), null, [], 'PDF bytes']) {
    await assert.rejects(createSubmissionArchive(bytes, 'Acme', date), /Choose a PDF/u);
  }
});

test('unavailable or failed hashing produces no ZIP and reports no private input', async t => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  t.after(() => Object.defineProperty(globalThis, 'crypto', original));
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {} });
  await assert.rejects(createSubmissionArchive(pdf, 'PRIVATE_LABEL', date), error =>
    error instanceof SubmissionArchiveError && /SHA-256 is unavailable/u.test(error.message));
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {
    subtle: { digest: async () => { throw new Error('PRIVATE_HASH_ERROR'); } },
  } });
  await assert.rejects(createSubmissionArchive(pdf, 'PRIVATE_LABEL', date), error => {
    assert.equal(error.message, 'Could not calculate the PDF hash. Try again in a current browser.');
    return true;
  });
});
