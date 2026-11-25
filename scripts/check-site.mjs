// Check the generated site, including links used under a GitHub Pages subfolder.
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import assert from 'node:assert/strict';

const root = resolve('dist');
const repository = (process.env.GITHUB_REPOSITORY ?? '').split('/')[1];
const pagesBase = process.env.GITHUB_PAGES === 'true' && repository && !repository.endsWith('.github.io') ? `/${repository}/` : '/';
const base = process.env.BASE_PATH || pagesBase;
function files(folder) {
  return readdirSync(folder, { withFileTypes: true }).flatMap((file) => file.isDirectory() ? files(join(folder, file.name)) : [join(folder, file.name)]);
}
const htmlFiles = files(root).filter((file) => file.endsWith('.html'));
for (const file of htmlFiles) {
  const html = readFileSync(file, 'utf8');
  assert.match(html, /<h1[ >]/, `Missing heading: ${file}`);
  assert.match(html, /name="description"/, `Missing description: ${file}`);
  for (const match of html.matchAll(/(?:href|src|data-model|data-topology)="([^"#]+)"/g)) {
    const url = new URL(match[1], 'https://local.test');
    if (url.origin !== 'https://local.test') continue;
    assert.ok(url.pathname.startsWith(base), `Link outside base: ${match[1]} in ${file}`);
    let target = resolve(root, decodeURIComponent(url.pathname.slice(base.length)));
    if (url.pathname.endsWith('/')) target = join(target, 'index.html');
    assert.ok(existsSync(target), `Broken link: ${match[1]} in ${file}`);
  }
}
for (const language of ['', 'ru/', 'fi/']) {
  for (const page of ['', 'projects/', 'models/', 'about/', ...['cafe', 'full-scene', 'forest', 'island', 'night-room'].map((slug) => `projects/${slug}/`)]) {
    assert.ok(existsSync(join(root, language, page, 'index.html')), `Missing page: ${language}${page}`);
  }
  for (const page of ['', 'projects/', 'models/']) {
    const html = readFileSync(join(root, language, page, 'index.html'), 'utf8');
    const cafe = html.indexOf(`${base}${language}projects/cafe/`);
    const fullScene = html.indexOf(`${base}${language}projects/full-scene/`);
    const forest = html.indexOf(`${base}${language}projects/forest/`);
    assert.ok(cafe >= 0 && fullScene > cafe && forest > fullScene, `FullScene must be second: ${language}${page}`);
  }
  for (const slug of ['cafe', 'island']) {
    const html = readFileSync(join(root, language, 'projects', slug, 'index.html'), 'utf8');
    assert.ok(html.includes('data-lighting="soft"'), `Expected softer studio light: ${language}${slug}`);
  }
}
const model = readFileSync(join(root, 'models/night-room.glb'));
const document = JSON.parse(model.subarray(20, 20 + model.readUInt32LE(12)).toString());
for (const name of ['Cube.006', 'Cube.015', 'Cube.027', 'Cube.028', 'Plane.011', 'Plane.013']) {
  assert.ok(!document.nodes.some((node) => node.name === name), `Night Room still contains helper: ${name}`);
}
assert.ok(document.images.length > 0 && document.images.every((image) => image.bufferView !== undefined), 'Night Room textures must be embedded');
const island = readFileSync(join(root, 'models/island.glb'));
const islandDocument = JSON.parse(island.subarray(20, 20 + island.readUInt32LE(12)).toString());
const roof = islandDocument.materials.find((material) => material.name === 'Material.009');
assert.ok(roof?.pbrMetallicRoughness.baseColorTexture, 'Island roof must retain its baked procedural color');
console.log(`Checked ${htmlFiles.length} pages, internal links, assets and Night Room export. Base: ${base}`);
