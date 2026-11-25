import type { APIRoute } from 'astro';
import { getProjects } from '../data/projects';
import { locales, pagePath } from '../i18n/paths';

export const GET: APIRoute = async ({ site }) => {
  const projects = await getProjects();
  const pages = ['', 'about/', 'projects/', 'models/', ...projects.map((project) => `projects/${project.slug}/`)];
  const urls = site ? locales.flatMap((locale) => pages.map((page) => `<url><loc>${new URL(pagePath(locale, page), site)}</loc></url>`)).join('') : '';
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`, { headers: { 'Content-Type': 'application/xml' } });
};
