import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkTextLimit } from '../src/text-limits.mjs';

test('counts the complete text without assuming a form limit', () => {
  assert.deepEqual(checkTextLimit(''), { count: 0, status: 'unset' });
  assert.deepEqual(checkTextLimit(' A\n\nB\t '), { count: 7, status: 'unset' });
  assert.deepEqual(checkTextLimit('Draft', ' \t '), { count: 5, status: 'unset' });
});

test('the form limit is inclusive and accepts an empty draft', () => {
  assert.deepEqual(checkTextLimit('Draft', '5'), { count: 5, limit: 5, status: 'within' });
  assert.deepEqual(checkTextLimit('Draft!', '5'), { count: 6, limit: 5, status: 'over' });
  assert.deepEqual(checkTextLimit('', '5'), { count: 0, limit: 5, status: 'within' });
  assert.deepEqual(checkTextLimit('Draft', ' 006 '), { count: 5, limit: 6, status: 'within' });
});

test('counts UTF-16 units like native HTML text fields without normalizing text', () => {
  assert.deepEqual(checkTextLimit('A😀é\ne\u0301', '7'), { count: 7, limit: 7, status: 'within' });
  assert.equal(checkTextLimit('😀', '1').status, 'over');
  assert.equal(checkTextLimit('研究', '2').status, 'within');
  assert.equal(checkTextLimit('e\u0301', '1').status, 'over');
});

test('invalid limits keep the count and never report that the text fits', () => {
  for (const value of ['0', '-1', '1.5', '1e3', '1,000', '0x10', '+5', 'five', 'NaN', 'Infinity', '9'.repeat(33), '9007199254740992']) {
    assert.deepEqual(checkTextLimit('Draft', value), { count: 5, status: 'invalid' }, value);
  }
  assert.deepEqual(checkTextLimit('Draft', '9007199254740991'), {
    count: 5, limit: Number.MAX_SAFE_INTEGER, status: 'within',
  });
});

test('large drafts retain their full count above a smaller form limit', () => {
  assert.deepEqual(checkTextLimit('A'.repeat(500_100), '1000'), {
    count: 500_100, limit: 1000, status: 'over',
  });
  assert.throws(() => checkTextLimit(null, '1000'), TypeError);
});
