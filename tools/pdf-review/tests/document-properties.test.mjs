import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inspectProperties, readProperties } from '../src/document-properties.mjs';

test('PDF and XMP keep conflicting values instead of selecting a winner', () => {
  const metadata = new Map([['dc:title', 'Old title'], ['dc:creator', ['First Author', 'Second Author']]]);
  const result = inspectProperties({ info: { Title: 'Current title', Author: 'Current Author' }, metadata });
  assert.deepEqual(result.fields, [
    { label: 'Title', source: 'PDF', value: 'Current title', limited: false },
    { label: 'Title', source: 'XMP', value: 'Old title', limited: false },
    { label: 'Author', source: 'PDF', value: 'Current Author', limited: false },
    { label: 'Author', source: 'XMP', value: 'First Author; Second Author', limited: false },
  ]);
  assert.equal(result.limited, false);
});

test('only named fields are read and raw XML is never requested', () => {
  const calls = [];
  const result = inspectProperties({
    info: { Title: 'Resume', Custom: 'Not inspected', CreationDate: 'D:20260928120000-04\'00\'' },
    metadata: { get: key => { calls.push(key); return null; }, getRaw: () => { throw new Error('Do not read XML'); } },
  });
  assert.equal(calls.length, 8);
  assert.equal(result.fields.length, 2);
  assert.equal(result.fields[1].value, 'D:20260928120000-04\'00\'');
  assert.equal(JSON.stringify(result).includes('Not inspected'), false);
});

test('absent and empty fields do not become invented values', () => {
  assert.deepEqual(inspectProperties({ info: { Title: '', Author: null }, metadata: new Map() }), { fields: [], limited: false });
  assert.deepEqual(inspectProperties({}), { fields: [], limited: false });
});

test('large values and lists are bounded without splitting surrogate pairs', () => {
  const result = inspectProperties({
    info: { Title: 'a'.repeat(1023) + '😀 remainder', Keywords: 'x'.repeat(100_000) },
    metadata: new Map([['dc:creator', Array.from({ length: 1000 }, (_, index) => `Author ${index}`)]]),
  });
  assert.equal(result.limited, true);
  for (const field of result.fields) {
    assert.ok(field.value.length <= 1024);
    assert.equal(field.value.isWellFormed(), true);
    assert.equal(field.limited, true);
  }
  const authors = result.fields.find(field => field.label === 'Author').value;
  assert.ok(authors.includes('Author 15'));
  assert.equal(authors.includes('Author 16'), false);
});

test('unsupported values and a failed field are reported without losing other fields', () => {
  const result = inspectProperties({
    info: { Author: { private: 'Never stringify objects' }, Producer: 'PDF writer' },
    metadata: { get: key => { if (key === 'dc:title') throw new Error('Private failure details'); return null; } },
  });
  assert.equal(result.limited, true);
  assert.deepEqual(result.fields, [{ label: 'PDF producer', source: 'PDF', value: 'PDF writer', limited: false }]);
  assert.equal(JSON.stringify(result).includes('Private'), false);
});

test('markup and control characters remain data for the UI to display safely', () => {
  const value = '<img src="https://example.test/private" onerror="alert(1)">\u202e';
  assert.equal(inspectProperties({ info: { Title: value } }).fields[0].value, value);
});

test('a normal property read returns bounded data', async () => {
  const result = await readProperties({ getMetadata: async () => ({ info: { Title: 'Resume' } }) });
  assert.equal(result.status, 'ok');
  assert.equal(result.fields[0].value, 'Resume');
});

test('metadata rejection, malformed results, and timeouts are isolated from the review', async () => {
  for (const getMetadata of [
    async () => { throw new Error('Private document details'); },
    async () => undefined,
    () => new Promise(() => {}),
  ]) {
    assert.deepEqual(await readProperties({ getMetadata }, { timeoutMs: 5 }), {
      status: 'unavailable', fields: [], limited: false,
    });
  }
});

test('cancellation skips unstarted reads and discards pending results', async () => {
  const controller = new AbortController();
  controller.abort();
  let calls = 0;
  const skipped = await readProperties({ getMetadata: () => { calls += 1; } }, { signal: controller.signal });
  assert.equal(calls, 0);
  assert.equal(skipped.status, 'cancelled');
  const pendingController = new AbortController();
  const pending = readProperties({ getMetadata: () => new Promise(() => {}) }, { signal: pendingController.signal });
  pendingController.abort();
  assert.deepEqual(await pending, { status: 'cancelled', fields: [], limited: false });
});

test('property timeouts cannot be disabled or extended accidentally', async () => {
  for (const timeoutMs of [0, -1, 5001, Infinity, NaN, '5']) {
    await assert.rejects(readProperties({}, { timeoutMs }), RangeError);
  }
});
