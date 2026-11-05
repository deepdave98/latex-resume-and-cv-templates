import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { unzipSync } from 'fflate';
import { createSubmissionArchive, readSubmissionReceipt, verifySubmissionPDF, MAX_RECEIPT_BYTES, SubmissionArchiveError } from '../src/submission-archive.mjs';

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

function receiptFor(bytes = pdf, fields = {}) {
  return { pdf: 'resume-acme.pdf', bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'), ...fields };
}

test('a saved browser receipt verifies original bytes without using the label, date, or current filename', async () => {
  const { receipt } = await contents(await createSubmissionArchive(pdf, 'Acme', date));
  const parsed = readSubmissionReceipt(JSON.stringify(receipt));
  assert.deepEqual(Object.keys(parsed), ['pdf', 'bytes', 'sha256']);
  assert.ok(Object.isFrozen(parsed));
  assert.deepEqual(await verifySubmissionPDF(pdf, parsed), { status: 'match' });
  const minimal = readSubmissionReceipt(JSON.stringify(receiptFor(pdf, { pdf: 'Renamed.PDF', sha256: receipt.sha256.toUpperCase() })));
  assert.deepEqual(await verifySubmissionPDF(pdf, minimal), { status: 'match' });
});

test('receipt reading handles escaped keys and quotes without treating label text as fields', () => {
  const receipt = receiptFor(pdf, { label: 'Acme "pdf": "other.pdf", \\"bytes\\": 0, Québec', saved_at: 'not authenticated' });
  const text = JSON.stringify(receipt).replace('"bytes":', '"by\\u0074es":');
  assert.deepEqual(readSubmissionReceipt(text), receiptFor());
  for (const suffix of ['"pdf":"resume-acme.pdf"', '"p\\u0064f":"resume-acme.pdf"', '"label":"Acme"', '"by\\u0074es":1']) {
    assert.throws(() => readSubmissionReceipt(`${JSON.stringify(receipt).slice(0, -1)},${suffix}}`), /duplicate/u);
  }
});

test('malformed or nested receipts produce no result and never echo private text', () => {
  const invalid = [
    '', '{"PRIVATE_LABEL":', '"PRIVATE_LABEL"', 'null', '[]', 'true', '17',
    JSON.stringify(receiptFor(pdf, { label: { private: 'PRIVATE_LABEL' } })),
    JSON.stringify(receiptFor(pdf, { extra: ['PRIVATE_LABEL'] })),
  ];
  for (const text of invalid) {
    assert.throws(() => readSubmissionReceipt(text), error => {
      assert.ok(error instanceof SubmissionArchiveError);
      assert.equal(error.message.includes('PRIVATE_LABEL'), false);
      return true;
    });
  }
  assert.throws(() => readSubmissionReceipt(null), SubmissionArchiveError);
});

test('receipt limits count UTF-8 bytes and accept the exact boundary', () => {
  const text = JSON.stringify(receiptFor());
  assert.deepEqual(readSubmissionReceipt(text.padEnd(MAX_RECEIPT_BYTES)), receiptFor());
  assert.throws(() => readSubmissionReceipt(text.padEnd(MAX_RECEIPT_BYTES + 1)), /too large/u);
  const unicode = JSON.stringify(receiptFor(pdf, { label: 'é'.repeat(MAX_RECEIPT_BYTES / 2) }));
  assert.ok(unicode.length < MAX_RECEIPT_BYTES);
  assert.throws(() => readSubmissionReceipt(unicode), /too large/u);
});

test('receipts require a portable PDF filename, an integer byte count, and a SHA-256 hash', () => {
  for (const [field, values] of [
    ['bytes', [null, true, false, 0, -1, 1.5, '1', Number.MAX_SAFE_INTEGER + 1]],
    ['sha256', [null, 1, true, '', 'a'.repeat(63), 'a'.repeat(65), 'z'.repeat(64)]],
    ['pdf', [null, 1, true, '', '../resume.pdf', '/resume.pdf', 'folder/resume.pdf', 'folder\\resume.pdf',
      'C:resume.pdf', 'resume.pdf:other.pdf', 'CON.pdf', 'con .pdf', 'NUL.pdf', 'COM1.pdf', 'COM¹.pdf',
      'LPT9.pdf', 'LPT².pdf', 'CONIN$.pdf', 'CONOUT$.pdf', 'resume?.pdf', 'resume*.pdf', 'resume|.pdf',
      'resume".pdf', 'resume<.pdf', 'resume>.pdf', 'resume\0.pdf', 'resume\n.pdf', 'resume\u200b.pdf',
      'resume\u00a0.pdf', '\ud800.pdf', '.', '..', '.pdf', '..pdf', 'resume.txt', 'resume.pdf ']],
  ]) {
    for (const value of values) {
      assert.throws(() => readSubmissionReceipt(JSON.stringify(receiptFor(pdf, { [field]: value }))), SubmissionArchiveError);
    }
    const missing = receiptFor();
    delete missing[field];
    assert.throws(() => readSubmissionReceipt(JSON.stringify(missing)), SubmissionArchiveError);
  }
  for (const name of ['resume.pdf', 'My Résumé.PDF', '软件.pdf', '.resume.pdf', 'resume..pdf', 'COM10.pdf']) {
    assert.equal(readSubmissionReceipt(JSON.stringify(receiptFor(pdf, { pdf: name }))).pdf, name);
  }
  for (const numericText of ['1.0', '1e0', '1.00000000000000000001']) {
    const text = JSON.stringify(receiptFor(new Uint8Array([1]))).replace('"bytes":1', `"bytes":${numericText}`);
    assert.throws(() => readSubmissionReceipt(text), /whole-number/u);
  }
});

test('verification distinguishes byte-count and same-size hash mismatches without modifying inputs', async () => {
  const receipt = readSubmissionReceipt(JSON.stringify(receiptFor()));
  const changed = new Uint8Array(pdf);
  changed[5] ^= 1;
  const before = new Uint8Array(changed);
  assert.deepEqual(await verifySubmissionPDF(pdf.subarray(0, -1), receipt), { status: 'size-mismatch' });
  assert.deepEqual(await verifySubmissionPDF(changed, receipt), { status: 'hash-mismatch' });
  assert.deepEqual(changed, before);
  assert.deepEqual(receipt, receiptFor());
  for (const bytes of [null, [], new Uint8Array(), 'PDF']) {
    await assert.rejects(verifySubmissionPDF(bytes, receipt), /Open the saved PDF/u);
  }
});

test('verification snapshots the selected bytes and expected hash before awaiting', async t => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  t.after(() => Object.defineProperty(globalThis, 'crypto', original));
  let release;
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {
    subtle: { digest: async (_algorithm, bytes) => {
      await new Promise(resolve => { release = resolve; });
      return createHash('sha256').update(bytes).digest();
    } },
  } });
  const buffer = new Uint8Array(pdf.length + 10);
  buffer.set(pdf, 4);
  const receipt = receiptFor();
  const pending = verifySubmissionPDF(buffer.subarray(4, pdf.length + 4), receipt);
  buffer.fill(0);
  receipt.sha256 = '0'.repeat(64);
  release();
  assert.deepEqual(await pending, { status: 'match' });
});

test('verification reports unavailable or failed hashing without leaking inputs', async t => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  t.after(() => Object.defineProperty(globalThis, 'crypto', original));
  const receipt = receiptFor(pdf, { pdf: 'PRIVATE_LABEL.pdf' });
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {} });
  assert.deepEqual(await verifySubmissionPDF(pdf.subarray(1), receipt), { status: 'size-mismatch' });
  await assert.rejects(verifySubmissionPDF(pdf, receipt), /SHA-256 is unavailable/u);
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {
    subtle: { digest: async () => { throw new Error('PRIVATE_HASH_ERROR'); } },
  } });
  await assert.rejects(verifySubmissionPDF(pdf, receipt), error => {
    assert.equal(error.message, 'Could not calculate the PDF hash. Try again in a current browser.');
    return true;
  });
});
