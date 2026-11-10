// Only publishes a previously built/tested tarball. Safe to rerun after success.
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';

const { name, version } = JSON.parse(readFileSync('packages/node/package.json', 'utf8'));
const files = readdirSync('dist').filter(file => file.endsWith('.tgz'));
if (files.length !== 1) throw new Error('Expected exactly one tested npm tarball');
const file = resolve('dist', files[0]);
const integrity = `sha512-${createHash('sha512').update(readFileSync(file)).digest('base64')}`;
const url = `https://registry.npmjs.org/${encodeURIComponent(name)}/${version}`;
const existing = await fetch(url);
if (existing.ok) {
  if ((await existing.json()).dist.integrity !== integrity) {
    throw new Error('Published version has different bytes. Do not replace a released version.');
  }
  console.log(`${name}@${version} already published with matching integrity.`);
} else if (existing.status === 404) {
  execFileSync('npm', ['publish', file, '--access', 'public', '--provenance'], { stdio: 'inherit' });
} else {
  throw new Error(`Registry availability check failed (${existing.status}); refusing to guess.`);
}
// npm can accept a release before its public registry has finished processing it.
// Poll metadata only: never replay the publication while it is processing.
for (let attempt = 0; attempt < 60; attempt++) {
  const verified = await fetch(url, { cache: 'no-store' });
  if (verified.ok) {
    if ((await verified.json()).dist.integrity !== integrity) {
      throw new Error('Published package differs from the tested artifact');
    }
    console.log(`${name}@${version} verified against the tested artifact.`);
    break;
  }
  if (verified.status !== 404 && verified.status < 500) {
    throw new Error(`Registry verification failed (${verified.status})`);
  }
  if (attempt === 59) throw new Error('npm is still processing the release; retry verification later.');
  await new Promise(resolve => setTimeout(resolve, 5000));
}
