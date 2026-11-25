// @ts-check
import { defineConfig } from 'astro/config';

const [owner, repository] = (process.env.GITHUB_REPOSITORY ?? '').split('/');
const onPages = process.env.GITHUB_PAGES === 'true';
const site = process.env.SITE_URL || (onPages && owner ? `https://${owner}.github.io` : undefined);
const base = process.env.BASE_PATH || (onPages && repository && !repository.endsWith('.github.io') ? `/${repository}` : '/');

export default defineConfig({
  site, base,
  output: 'static',
  trailingSlash: 'always',
  i18n: { defaultLocale: 'en', locales: ['en', 'ru', 'fi'], routing: { prefixDefaultLocale: false } },
});
