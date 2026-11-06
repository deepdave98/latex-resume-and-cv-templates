import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatFileSize } from '../src/file-size.mjs';

test('file size shows KB below one MB and always the exact bytes', () => {
  assert.equal(formatFileSize(1_000_001), '1.00 MB (1,000,001 bytes)');
  assert.equal(formatFileSize(21_403), '21.4 KB (21,403 bytes)');
  assert.equal(formatFileSize(500), '0.5 KB (500 bytes)');
  assert.equal(formatFileSize(undefined), 'File size unavailable');
});
