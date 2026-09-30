import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkUploadLimits, formatFileSize } from '../src/upload-limits.mjs';

test('no portal limits are assumed', () => {
  assert.deepEqual(checkUploadLimits({ bytes: 3_000_000, pages: 4 }), {
    pages: { status: 'unset' }, size: { status: 'unset' },
  });
});

test('file and page limits are independent and inclusive', () => {
  assert.deepEqual(checkUploadLimits({ bytes: 2_000_000, pages: 2 }, { maxPages: '2', maxMB: '2' }), {
    pages: { status: 'within', limit: 2 }, size: { status: 'within', limit: 2_000_000 },
  });
  assert.deepEqual(checkUploadLimits({ bytes: 2_000_001, pages: 3 }, { maxPages: '2', maxMB: '2' }), {
    pages: { status: 'over', limit: 2 }, size: { status: 'over', limit: 2_000_000 },
  });
  assert.equal(checkUploadLimits({ bytes: 1, pages: 2 }, { maxPages: '1' }).pages.status, 'over');
  assert.equal(checkUploadLimits({ bytes: 1, pages: 2 }, { maxMB: '1' }).pages.status, 'unset');
});

test('fractional MB limits compare exact bytes, not rounded display sizes', () => {
  for (const [value, limit] of [['0.5', 500_000], ['1.000001', 1_000_001], ['0.000249', 249]]) {
    assert.equal(checkUploadLimits({ bytes: limit, pages: 1 }, { maxMB: value }).size.status, 'within');
    assert.equal(checkUploadLimits({ bytes: limit + 1, pages: 1 }, { maxMB: value }).size.status, 'over');
  }
  assert.equal(checkUploadLimits({ bytes: 1_048_576, pages: 1 }, { maxMB: '1' }).size.status, 'over');
});

test('invalid limits never produce a passing check or disable the other check', () => {
  for (const value of ['0', '-1', 'NaN', 'Infinity', '2e3', '1,5', '2 MB', '1.0000001', '9'.repeat(100)]) {
    const result = checkUploadLimits({ bytes: 1, pages: 1 }, { maxPages: value, maxMB: value });
    assert.equal(result.pages.status, 'invalid', value);
    assert.equal(result.size.status, 'invalid', value);
  }
  assert.equal(checkUploadLimits({ bytes: 1, pages: 1 }, { maxPages: '1.5' }).pages.status, 'invalid');
  const result = checkUploadLimits({ bytes: 1, pages: 1 }, { maxPages: 'bad', maxMB: '1' });
  assert.equal(result.pages.status, 'invalid');
  assert.equal(result.size.status, 'within');
});

test('missing or unusable file facts cannot pass', () => {
  for (const value of [undefined, null, 0, -1, NaN, Infinity, 1.5, Number.MAX_SAFE_INTEGER + 1]) {
    const result = checkUploadLimits({ bytes: value, pages: value }, { maxPages: '2', maxMB: '2' });
    assert.equal(result.pages.status, 'unknown');
    assert.equal(result.size.status, 'unknown');
  }
});

test('whitespace and leading zeroes do not change a valid limit', () => {
  assert.deepEqual(checkUploadLimits({ bytes: 500_000, pages: 2 }, { maxPages: ' 02 ', maxMB: ' 00.5 ' }), {
    pages: { status: 'within', limit: 2 }, size: { status: 'within', limit: 500_000 },
  });
  assert.equal(checkUploadLimits({}, { maxPages: ' \t ' }).pages.status, 'unset');
});

test('file size includes exact bytes even when the MB display rounds down', () => {
  assert.equal(formatFileSize(1_000_001), '1.00 MB (1,000,001 bytes)');
  assert.equal(formatFileSize(500), '0.00 MB (500 bytes)');
  assert.equal(formatFileSize(undefined), 'File size unavailable');
});
