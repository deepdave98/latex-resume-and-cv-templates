import assert from 'node:assert/strict';
import test from 'node:test';
import { createComparisonSnapshot, compareSnapshots } from '../src/compare.mjs';
import { displayDestination, inspectLinkAnnotations, reviewDocument } from '../src/review.mjs';

const external = (destination, resolvedDestination = destination) => ({ type: 'external', destination, resolvedDestination, truncated: false });
const page = (text = 'Built a useful tool.', links = []) => ({ number: 1, text,
  textStatus: 'ok', textTruncated: false, linksStatus: 'ok', links, warnings: [] });
const review = (pages = [page()]) => ({ pages, pageCount: pages.length, reviewedPageCount: pages.length });
const snapshot = (text, links = []) => createComparisonSnapshot(review([page(text, links)]), { filename: 'resume.pdf', bytes: 123 });
const words = text => (text.match(/\S+/gu) ?? []).join(' ');

test('snapshots use original page extraction and own no mutable review data', () => {
  const source = review([page('Original facts', [external('mailto:before@example.test')])]);
  source.text = 'An application-form draft must not replace PDF text';
  const before = createComparisonSnapshot(source, { filename: 'before.pdf', bytes: 456 });
  source.pages[0].text = 'Edited facts';
  source.pages[0].links[0].destination = 'mailto:after@example.test';
  source.pages.push(page('Another page'));
  assert.equal(before.text.value, 'Original facts');
  assert.equal(before.links.values[0].destination, 'mailto:before@example.test');
  assert.throws(() => { before.text.value = 'Changed'; }, TypeError);
  assert.throws(() => { before.links.values[0].destination = 'Changed'; }, TypeError);
  assert.throws(() => { before.links.values.push(external('x')); }, TypeError);
  const comparison = compareSnapshots(before, snapshot('Original facts', [external('mailto:before@example.test')]));
  assert.deepEqual(comparison.before, { filename: 'before.pdf', bytes: 456, pageCount: 1 });
  assert.equal(comparison.text.status, 'same');
  assert.equal(comparison.links.status, 'same');
});

test('whitespace and line wrapping alone do not produce text changes', () => {
  const result = compareSnapshots(snapshot('Built\n a\ttool.\n\n2025'), snapshot('  Built a tool. 2025 '));
  assert.deepEqual(result.text, { status: 'same', changes: [], reason: '' });
});

test('text matching preserves punctuation, case, numbers, Unicode, and hyphens', () => {
  for (const [before, after] of [
    ['Latency 80 ms.', 'Latency 18 ms.'], ['Built API.', 'Built API!'],
    ['GitHub', 'Github'], ['é', 'e\u0301'], ['A', 'Ａ'], ['😀', '😃'],
    ['inter-\nface', 'interface'], ['ab', 'a b'], ['https://one.test', 'http://one.test'],
  ]) assert.equal(compareSnapshots(snapshot(before), snapshot(after)).text.status, 'changed', `${before} → ${after}`);
});

test('added, removed, reordered, and repeated words reconstruct both originals', () => {
  const samples = ['A', 'A B', 'B A', 'A A B', 'A C B', 'B C D', 'one two three four'];
  for (const before of samples) {
    for (const after of samples) {
      const result = compareSnapshots(snapshot(before), snapshot(after)).text;
      assert.equal(result.status, before === after ? 'same' : 'changed');
      if (result.status === 'same') continue;
      const restore = omitted => words(result.changes.filter(change => change.type !== omitted).map(change => change.text).join(' '));
      assert.equal(restore('added'), before);
      assert.equal(restore('removed'), after);
    }
  }
});

test('a page-count change stays visible even when the extracted words match', () => {
  const before = snapshot('First second');
  const after = createComparisonSnapshot(review([page('First'), { ...page('second'), number: 2 }]), { filename: 'two-pages.pdf', bytes: 999 });
  const result = compareSnapshots(before, after);
  assert.equal(result.text.status, 'same');
  assert.equal(result.before.pageCount, 1);
  assert.equal(result.after.pageCount, 2);
  assert.equal(result.after.bytes, 999);
});

test('empty, failed, truncated, and form-field extraction never claims unchanged text', () => {
  const incomplete = [
    { ...page(), textStatus: 'error' }, { ...page(), textStatus: 'empty' },
    { ...page(), textStatus: 'limited' }, { ...page(), textTruncated: true },
    page(' \n '), { ...page(), warnings: [{ code: 'form-fields' }] },
  ];
  for (const record of incomplete) {
    const saved = createComparisonSnapshot(review([record]));
    for (const [before, after] of [[saved, saved], [saved, snapshot('Complete')], [snapshot('Complete'), saved]]) {
      const result = compareSnapshots(before, after);
      assert.equal(result.text.status, 'incomplete');
      assert.ok(result.text.reason);
      assert.deepEqual(result.text.changes, []);
    }
  }
});

test('known character extraction warnings prevent an unqualified text match', async () => {
  for (const character of ['\ufffd', '\ue000', '\u0000']) {
    const result = await reviewDocument({ numPages: 1, getPage: async () => ({
      getTextContent: async () => ({ items: [{ str: `Applicant ${character}` }] }),
      getAnnotations: async () => [],
    }) });
    const saved = createComparisonSnapshot(result);
    const comparison = compareSnapshots(saved, saved);
    assert.equal(comparison.text.status, 'incomplete');
    assert.match(comparison.text.reason, /characters need manual review/);
    assert.equal(comparison.links.status, 'same');
  }
});

test('valid direction controls and Unicode joiners remain literal comparable text', async () => {
  for (const character of ['\u202e', '\u2066', '\u200d']) {
    const result = await reviewDocument({ numPages: 1, getPage: async () => ({
      getTextContent: async () => ({ items: [{ str: `Applicant ${character}Name` }] }),
      getAnnotations: async () => [],
    }) });
    const saved = createComparisonSnapshot(result);
    assert.equal(compareSnapshots(saved, saved).text.status, 'same');
    assert.equal(compareSnapshots(saved, snapshot('Applicant Name')).text.status, 'changed');
  }
});

test('missing, duplicate, and unordered pages prevent complete comparisons', () => {
  for (const source of [undefined, review([]), { ...review(), pageCount: 2 },
    { ...review(), reviewedPageCount: 0 }, review([{ ...page(), number: 2 }]),
    review([page(), page()])]) {
    const saved = createComparisonSnapshot(source);
    const result = compareSnapshots(saved, saved);
    assert.equal(result.text.status, 'incomplete');
    assert.equal(result.links.status, 'incomplete');
  }
});

test('a top-level truncation flag without page details still blocks unchanged claims', () => {
  for (const links of [[], [{ type: 'internal', destination: 'Page 1' }]]) {
    const saved = createComparisonSnapshot({ ...review([page('Text', links)]), truncated: true });
    const result = compareSnapshots(saved, saved);
    assert.equal(result.text.status, 'incomplete');
    assert.equal(result.links.status, 'incomplete');
  }
});

test('a known link-only truncation does not discard complete text comparison', () => {
  const saved = createComparisonSnapshot({ ...review([{ ...page(), linksStatus: 'limited' }]), truncated: true });
  const result = compareSnapshots(saved, saved);
  assert.equal(result.text.status, 'same');
  assert.equal(result.links.status, 'incomplete');
});

test('comparison input and work limits cannot turn unexamined text into a match', () => {
  for (const text of ['x'.repeat(60_001), 'a '.repeat(8_001)]) {
    const result = compareSnapshots(snapshot(text), snapshot(text)).text;
    assert.ok(['incomplete', 'limited'].includes(result.status));
    assert.ok(result.reason);
    assert.deepEqual(result.changes, []);
  }
  const large = prefix => Array.from({ length: 1_001 }, (_, index) => `${prefix}${index}`).join(' ');
  assert.equal(compareSnapshots(snapshot(large('a')), snapshot(large('b'))).text.status, 'limited');
});

test('a small change in a long common document remains comparable', () => {
  const common = 'same '.repeat(3_000);
  const result = compareSnapshots(snapshot(`${common}old ${common}`), snapshot(`${common}new ${common}`)).text;
  assert.equal(result.status, 'changed');
  assert.deepEqual(result.changes.filter(change => change.type !== 'equal'), [
    { type: 'removed', text: 'old' }, { type: 'added', text: 'new' },
  ]);
});

test('separate-change and output bounds produce a limited result', () => {
  const many = prefix => Array.from({ length: 150 }, (_, index) => `${prefix}${index} shared${index}`).join(' ');
  assert.equal(compareSnapshots(snapshot(many('a')), snapshot(many('b'))).text.status, 'limited');
  assert.equal(compareSnapshots(snapshot('a'.repeat(45_000)), snapshot('b'.repeat(45_000))).text.status, 'limited');
});

test('link differences count duplicate destinations and preserve literal protocols', () => {
  const before = snapshot('Text', [external('https://one.test'), external('https://one.test'), external('http://two.test')]);
  const after = snapshot('Text', [external('https://one.test'), external('https://two.test')]);
  const result = compareSnapshots(before, after).links;
  assert.equal(result.status, 'changed');
  assert.deepEqual(result.removed, [
    { type: 'external', destination: 'https://one.test', resolvedDestination: 'https://one.test', count: 1 },
    { type: 'external', destination: 'http://two.test', resolvedDestination: 'http://two.test', count: 1 },
  ]);
  assert.deepEqual(result.added, [{ type: 'external', destination: 'https://two.test', resolvedDestination: 'https://two.test', count: 1 }]);
  assert.equal(compareSnapshots(after, snapshot('Text', [...after.links.values].reverse())).links.status, 'same');
});

test('link comparison keeps hidden controls and markup as inert data', () => {
  const destination = 'https://example.test/\u202e<img onerror=alert(1)>';
  const result = compareSnapshots(snapshot('Text'), snapshot('Text', [external(destination)])).links;
  assert.equal(result.status, 'changed');
  assert.equal(result.added[0].destination, destination);
  assert.equal(displayDestination(result.added[0].destination), 'https://example.test/\\u202e<img onerror=alert(1)>');
});

test('the same raw URL with a changed resolved destination is a link change', async () => {
  const extract = async url => reviewDocument({ numPages: 1, getPage: async () => ({
    getTextContent: async () => ({ items: [{ str: 'Profile' }] }),
    getAnnotations: async () => [{ subtype: 'Link', unsafeUrl: '/profile', url }],
  }) });
  const before = createComparisonSnapshot(await extract('https://old.test/profile'));
  const after = createComparisonSnapshot(await extract('https://new.test/profile'));
  const result = compareSnapshots(before, after);
  assert.equal(result.text.status, 'same');
  assert.equal(result.links.status, 'changed');
  assert.deepEqual(result.links.removed, [{ type: 'external', destination: '/profile', resolvedDestination: 'https://old.test/profile', count: 1 }]);
  assert.deepEqual(result.links.added, [{ type: 'external', destination: '/profile', resolvedDestination: 'https://new.test/profile', count: 1 }]);
});

test('raw and resolved pairs retain separate duplicate counts and missing values', () => {
  const a = external('/profile', 'https://a.test/profile');
  const b = external('/profile', 'https://b.test/profile');
  const before = snapshot('Profile', [a, a, b]);
  const after = snapshot('Profile', [a, b, b]);
  const result = compareSnapshots(before, after).links;
  assert.equal(result.removed[0].resolvedDestination, a.resolvedDestination);
  assert.equal(result.removed[0].count, 1);
  assert.equal(result.added[0].resolvedDestination, b.resolvedDestination);
  assert.equal(result.added[0].count, 1);
  assert.equal(compareSnapshots(snapshot('Profile', [external('/profile', null)]), snapshot('Profile', [a])).links.status, 'changed');
});

test('hidden controls in resolved destinations remain visible differences', () => {
  const annotations = resolved => inspectLinkAnnotations([{ subtype: 'Link', unsafeUrl: '/profile', url: resolved }]).links;
  const before = snapshot('Profile', annotations('https://example.test/profile'));
  const after = snapshot('Profile', annotations('https://example.test/\u202eprofile'));
  const result = compareSnapshots(before, after).links;
  assert.equal(result.status, 'changed');
  assert.equal(displayDestination(result.added[0].resolvedDestination), 'https://example.test/\\u202eprofile');
});

test('resolved destinations obey per-value and combined storage limits', () => {
  const overlong = inspectLinkAnnotations([{ subtype: 'Link', unsafeUrl: '/profile', url: `https://example.test/${'x'.repeat(4_100)}` }]).links;
  const combined = Array.from({ length: 5 }, (_, index) => external(`${index}${'a'.repeat(3_999)}`, 'b'.repeat(4_000)));
  for (const links of [overlong, [external('/profile', 'x'.repeat(4_097))], combined]) {
    const saved = snapshot('Profile', links);
    assert.equal(compareSnapshots(saved, saved).links.status, 'incomplete');
    assert.ok(saved.links.values.reduce((total, link) => total + link.destination.length + (link.resolvedDestination?.length ?? 0), 0) <= 32_000);
  }
});

test('unknown destinations, internal links, and actions never claim unchanged links', () => {
  for (const link of [{ type: 'unknown', destination: 'Unavailable' },
    { type: 'internal', destination: 'Page 1' }, { type: 'action', destination: 'Print' },
    external(''), { ...external('https://example.test'), truncated: true }]) {
    const saved = snapshot('Text', [link]);
    const result = compareSnapshots(saved, saved);
    assert.equal(result.links.status, 'incomplete');
    assert.ok(result.links.reason);
    assert.equal(result.text.status, 'same');
  }
});

test('partial link inspection can show known changes without declaring completeness', () => {
  const before = createComparisonSnapshot(review([{ ...page('Text', [external('https://old.test')]), linksStatus: 'error' }]));
  const result = compareSnapshots(before, snapshot('Text', [external('https://new.test')])).links;
  assert.equal(result.status, 'incomplete');
  assert.equal(result.removed[0].destination, 'https://old.test');
  assert.equal(result.added[0].destination, 'https://new.test');
});

test('link count and destination limits retain only bounded reference data', () => {
  for (const links of [Array.from({ length: 101 }, (_, index) => external(`https://example.test/${index}`)),
    [external('x'.repeat(4_097))], Array.from({ length: 9 }, () => external('x'.repeat(4_000)))]) {
    const saved = snapshot('Text', links);
    assert.ok(saved.links.values.length <= 100);
    assert.ok(saved.links.values.reduce((total, link) => total + link.destination.length + (link.resolvedDestination?.length ?? 0), 0) <= 32_000);
    assert.equal(compareSnapshots(saved, saved).links.status, 'incomplete');
  }
});

test('snapshots preserve safe summary values and reject unrelated comparison objects', () => {
  const saved = createComparisonSnapshot(review(), { filename: 'x'.repeat(1_000), bytes: Infinity });
  assert.equal(saved.filename.length, 255);
  assert.equal(saved.bytes, null);
  const unicode = createComparisonSnapshot(review(), { filename: `${'x'.repeat(254)}😀.pdf` });
  assert.equal(unicode.filename, 'x'.repeat(254));
  assert.throws(() => compareSnapshots({}, saved), TypeError);
  assert.throws(() => compareSnapshots(saved, null), TypeError);
});

test('the actual reviewDocument result supplies the snapshot contract', async () => {
  const original = await reviewDocument({ numPages: 1, getPage: async () => ({
    getTextContent: async () => ({ items: [{ str: 'Built a tool.' }] }),
    getAnnotations: async () => [{ subtype: 'Link', url: 'mailto:person@example.test' }],
  }) });
  const result = compareSnapshots(createComparisonSnapshot(original), snapshot('Built a better tool.', [external('mailto:person@example.test')]));
  assert.equal(result.text.status, 'changed');
  assert.equal(result.links.status, 'same');
});
