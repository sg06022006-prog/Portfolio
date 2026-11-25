import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { asset } from '../i18n/paths';

// A changed model gets a new URL, so old cached geometry cannot reappear.
export function versionedAsset(path: string) {
  const file = resolve(process.cwd(), 'public', decodeURIComponent(path.replace(/^\//, '')));
  const version = createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 10);
  return `${asset(path)}?v=${version}`;
}
