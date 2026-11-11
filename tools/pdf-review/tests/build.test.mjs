import { test } from 'node:test';
import assert from 'node:assert/strict';
import { copyFile, cp, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { createHash } from 'node:crypto';
import { unzipSync } from 'fflate';

// Resolve from this file explicitly, not from the caller's working directory.
const output = new URL('../../../downloads/pdf-review.html', import.meta.url);
const page = await readFile(output, 'utf8');

test('the downloadable ZIP contains exactly the self-contained page', async () => {
  const zip = unzipSync(await readFile(new URL('../../../downloads/pdf-review.zip', import.meta.url)));
  assert.deepEqual(Object.keys(zip), ['pdf-review.html']);
  assert.equal(new TextDecoder().decode(zip['pdf-review.html']), page);
});

test('CSP hashes match the exact inline script and stylesheet', () => {
  const scripts = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  const styles = [...page.matchAll(/<style>([\s\S]*?)<\/style>/g)];
  assert.equal(scripts.length, 1);
  assert.equal(styles.length, 1);
  for (const [, content] of [...scripts, ...styles]) {
    const hash = createHash('sha256').update(content).digest('base64');
    assert.ok(page.includes(`'sha256-${hash}'`));
  }
  assert.ok(!page.includes('<!-- APP_SCRIPT -->'));
  assert.ok(!page.includes('<!-- APP_CSP -->'));
});

test('policy blocks connections, external code, plugins, and form submission', () => {
  const policy = page.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/)[1];
  for (const directive of ["default-src 'none'", "connect-src 'none'", "object-src 'none'", "base-uri 'none'", "form-action 'none'", 'worker-src blob:']) assert.ok(policy.includes(directive));
  assert.ok(!policy.includes("'unsafe-eval'"));
  assert.ok(!policy.includes("'unsafe-inline'"));
  assert.ok(!policy.includes('https:'));
  assert.ok(!/<script[^>]+src=|<link[^>]+rel="stylesheet"|<iframe|<object/i.test(page));
});

test('app and third-party licenses travel inside the offline download', () => {
  for (const phrase of ['Copyright (c) 2026 deepdave98', 'Apache License', 'LICENSE_FOXIT', 'LICENSE_LIBERATION', 'LICENSE_OPENJPEG', 'LICENSE_JBIG2']) assert.ok(page.includes(phrase));
});

test('build replaces complete outputs and preserves previous files on write failure', { timeout: 60_000 }, async t => {
  const run = promisify(execFile);
  for (const target of [null, 'pdf-review.html', 'pdf-review.zip']) {
    await t.test(target ? `failed ${target} write` : 'successful build', async t => {
      const root = await mkdtemp(path.join(tmpdir(), 'pdf reviewer build '));
      t.after(() => rm(root, { recursive: true, force: true }));
      const app = path.join(root, 'tools', 'pdf-review');
      const downloads = path.join(root, 'downloads');
      await mkdir(app, { recursive: true });
      await mkdir(downloads);
      for (const name of ['build.mjs', 'index.html', 'styles.css']) {
        await copyFile(new URL(`../${name}`, import.meta.url), path.join(app, name));
      }
      await cp(new URL('../src/', import.meta.url), path.join(app, 'src'), { recursive: true });
      await copyFile(new URL('../../../LICENSE', import.meta.url), path.join(root, 'LICENSE'));
      await symlink(fileURLToPath(new URL('../node_modules', import.meta.url)), path.join(app, 'node_modules'), 'junction');
      const previous = new Map([
        ['pdf-review.html', Buffer.from('Previous complete HTML')],
        ['pdf-review.zip', Buffer.from('Previous complete ZIP')],
      ]);
      for (const [name, bytes] of previous) await writeFile(path.join(downloads, name), bytes);
      const inject = `
        import fs from 'node:fs/promises';
        import path from 'node:path';
        import { syncBuiltinESMExports } from 'node:module';
        const original = fs.writeFile;
        fs.writeFile = async (filename, data, options) => {
          if (path.basename(filename) === ${JSON.stringify(target)}) {
            await original(filename, 'partial write');
            throw new Error('Simulated output write failure');
          }
          return original(filename, data, options);
        };
        syncBuiltinESMExports();
        await import('./build.mjs');
      `;
      const command = run(process.execPath, ['--input-type=module', '-e', inject], {
        cwd: app, timeout: 25_000,
      });
      if (target) {
        await assert.rejects(command, error => {
          assert.match(error.stderr, /Simulated output write failure/u);
          return true;
        });
        for (const [name, bytes] of previous) {
          assert.deepEqual(await readFile(path.join(downloads, name)), bytes);
        }
      } else {
        await command;
        assert.equal(await readFile(path.join(downloads, 'pdf-review.html'), 'utf8'), page);
        assert.deepEqual(await readFile(path.join(downloads, 'pdf-review.zip')),
          await readFile(new URL('../../../downloads/pdf-review.zip', import.meta.url)));
      }
      assert.deepEqual((await readdir(downloads)).sort(), [...previous.keys()].sort());
    });
  }
});
