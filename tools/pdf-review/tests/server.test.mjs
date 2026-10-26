import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { copyFile, mkdir, mkdtemp, rm, unlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import test from 'node:test';

test('an absent build returns 503 and the server recovers when the page is built', { timeout: 15_000 }, async t => {
  const root = await mkdtemp(join(tmpdir(), 'pdf-review-server-'));
  const app = join(root, 'tools', 'pdf-review');
  await mkdir(app, { recursive: true });
  await copyFile(new URL('../server.mjs', import.meta.url), join(app, 'server.mjs'));
  const child = spawn(process.execPath, [join(app, 'server.mjs')], {
    cwd: tmpdir(), env: { ...process.env, PDF_REVIEW_PORT: '0' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let errors = '';
  child.stderr.on('data', chunk => { errors += chunk; });
  t.after(async () => {
    if (child.exitCode === null && child.signalCode === null) {
      child.kill();
      await once(child, 'exit');
    }
    await rm(root, { recursive: true, force: true });
  });
  const lines = createInterface({ input: child.stdout });
  const [startup] = await once(lines, 'line', { signal: AbortSignal.timeout(5000) });
  lines.close();
  assert.match(startup, /^PDF review: http:\/\/127\.0\.0\.1:[1-9]\d*$/u);
  const origin = startup.slice('PDF review: '.length);

  for (const path of ['/', '/pdf-review.html']) {
    const response = await fetch(origin + path);
    assert.equal(response.status, 503);
    assert.equal(await response.text(), 'Build the review page first.');
  }
  const missing = await fetch(origin + '/private.pdf');
  assert.equal(missing.status, 404);
  assert.equal(await missing.text(), '');

  const html = '<!doctype html><title>Local reviewer</title>';
  const page = join(root, 'downloads', 'pdf-review.html');
  await mkdir(join(root, 'downloads'));
  await writeFile(page, html);
  for (const path of ['/', '/pdf-review.html']) {
    const response = await fetch(origin + path);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('content-type'), 'text/html; charset=utf-8');
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.equal(await response.text(), html);
  }
  await unlink(page);
  const removed = await fetch(origin + '/');
  assert.equal(removed.status, 503);
  assert.equal(await removed.text(), 'Build the review page first.');
  assert.equal(child.exitCode, null, errors);
  assert.equal(errors, '');
});
