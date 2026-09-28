import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createTextDownload, textFilename, MAX_DRAFT_CHARS } from '../src/text-download.mjs';

test('text exports retain the PDF name with a text-only suffix', () => {
  assert.equal(textFilename('Ada Lovelace - Backend.PDF'), 'Ada Lovelace - Backend-text.txt');
  assert.equal(textFilename('resume-export'), 'resume-export-text.txt');
  assert.equal(textFilename('draft.exe'), 'draft.exe-text.txt');
  assert.equal(textFilename('CON.pdf'), 'CON-text.txt');
});

test('download names exclude paths, hidden controls, and invalid filename characters', () => {
  assert.equal(textFilename('../../resume.pdf'), 'resume-text.txt');
  assert.equal(textFilename('C:\\private\\resume.pdf'), 'resume-text.txt');
  assert.equal(textFilename('  .re\u202esume\u0000:*?<>|".pdf'), 'resume-text.txt');
  for (const filename of ['', '.pdf', '...', null, undefined, {}, '\u200b.pdf']) {
    assert.equal(textFilename(filename), 'resume-text.txt');
  }
});

test('international filenames keep whole characters within a portable byte length', () => {
  assert.equal(textFilename('Re\u0301sume\u0301.pdf'), 'Résumé-text.txt');
  for (const stem of ['a'.repeat(1000), '履歴書'.repeat(100), '😀'.repeat(100)]) {
    const result = textFilename(`${stem}.pdf`);
    assert.ok(new TextEncoder().encode(result).length <= 189);
    assert.ok(result.endsWith('-text.txt'));
    assert.equal(result.includes('\ufffd'), false);
    assert.equal(result.isWellFormed(), true);
  }
});

test('UTF-8 download contains exactly the edited text, without headings or metadata', async () => {
  const text = 'Zoë — 研究\n\n• Tested retries.\n<not HTML>\n';
  const result = createTextDownload('backend.pdf', text);
  assert.equal(result.filename, 'backend-text.txt');
  assert.equal(result.blob.type, 'text/plain;charset=utf-8');
  assert.equal(await result.blob.text(), text);
  assert.deepEqual(new Uint8Array(await result.blob.arrayBuffer()), new TextEncoder().encode(text));
});

test('empty, invalid, and oversized text cannot produce misleading exports', () => {
  for (const text of ['', ' \n\t', null, undefined, 0, {}, 'a'.repeat(MAX_DRAFT_CHARS + 1)]) {
    assert.throws(() => createTextDownload('resume.pdf', text), RangeError);
  }
  assert.equal(createTextDownload('resume.pdf', 'a'.repeat(MAX_DRAFT_CHARS)).blob.size, MAX_DRAFT_CHARS);
});
