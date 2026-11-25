import type { APIRoute } from 'astro';
import { asset } from '../i18n/paths';

export const GET: APIRoute = ({ site }) => new Response(
  `User-agent: *\nAllow: /\n${site ? `Sitemap: ${new URL(asset('sitemap.xml'), site)}\n` : ''}`,
  { headers: { 'Content-Type': 'text/plain' } },
);
