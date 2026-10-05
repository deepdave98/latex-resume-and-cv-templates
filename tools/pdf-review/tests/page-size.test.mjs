import assert from 'node:assert/strict';
import test from 'node:test';
import { formatPageSize } from '../src/page-size.mjs';

test('recognizes common paper sizes in either orientation', () => {
  assert.equal(formatPageSize(612, 792), 'US Letter · 8.5 × 11 in · Portrait');
  assert.equal(formatPageSize(792, 612), 'US Letter · 11 × 8.5 in · Landscape');
  assert.equal(formatPageSize(595.2756, 841.8898), 'A4 · 210 × 297 mm · Portrait');
  assert.equal(formatPageSize(841.8898, 595.2756), 'A4 · 297 × 210 mm · Landscape');
  assert.equal(formatPageSize(612, 1008), 'US Legal · 8.5 × 14 in · Portrait');
});

test('identifies rounded PDF page boxes but not nearby custom sizes', () => {
  assert.match(formatPageSize(595, 842), /^A4 ·/u);
  assert.match(formatPageSize(595.9, 841.5), /^A4 ·/u);
  assert.match(formatPageSize(597, 842), /^Custom size ·/u);
  assert.match(formatPageSize(614, 792), /^Custom size ·/u);
});

test('custom and square pages retain measured dimensions', () => {
  assert.equal(formatPageSize(432, 648), 'Custom size · 152.4 × 228.6 mm · Portrait');
  assert.equal(formatPageSize(648, 432), 'Custom size · 228.6 × 152.4 mm · Landscape');
  assert.equal(formatPageSize(720, 720), 'Custom size · 254 × 254 mm · Square');
});

test('unavailable geometry is never labelled as a paper size', () => {
  for (const value of [undefined, null, '612', 0, -1, NaN, Infinity, -Infinity]) {
    assert.equal(formatPageSize(value, 792), 'Page size unavailable');
    assert.equal(formatPageSize(612, value), 'Page size unavailable');
  }
});
