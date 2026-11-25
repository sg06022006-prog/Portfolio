export const locales = ['en', 'ru', 'fi'] as const;
export type Locale = typeof locales[number];

// BASE_URL is '/' locally and '/repository/' on GitHub project Pages.
export function asset(path: string) {
  if (/^(https?:|mailto:|#)/.test(path)) return path;
  return `${import.meta.env.BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}

export function pagePath(locale: Locale, page = '') {
  return asset(`${locale === 'en' ? '' : locale + '/'}${page.replace(/^\//, '')}`);
}

export function pageFromUrl(url: URL) {
  let path = url.pathname.slice(import.meta.env.BASE_URL.replace(/\/$/, '').length);
  path = path.replace(/^\//, '').replace(/^(ru|fi)\//, '');
  return path;
}
