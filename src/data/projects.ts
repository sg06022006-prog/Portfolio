import { getCollection, type CollectionEntry } from 'astro:content';
import { projectTranslations, factTranslations } from '../i18n/project-translations';
import { translator } from '../i18n/ui';
import type { Locale } from '../i18n/paths';

export type Project = CollectionEntry<'projects'>['data'] & { slug: string; preview: string; thumbnail: string };

export async function getProjects(locale: Locale = 'en'): Promise<Project[]> {
  const entries = await getCollection('projects');
  const t = translator(locale);
  return entries.map(({ id, data }) => {
    const translations = locale === 'en' ? undefined : projectTranslations[locale];
    const text = translations?.[id as keyof typeof translations];
    const fact = (value: string) => locale === 'en' ? value : factTranslations[value]?.[locale === 'ru' ? 0 : 1] ?? value;
    return {
      ...data,
      ...text,
      slug: id,
      preview: data.preview ?? data.image,
      thumbnail: data.thumbnail ?? data.preview ?? data.image,
      category: data.category.includes('ENVIRONMENT') ? `${t('art')} / ${t('focus')}` : t('art'),
      alt: `${t('renderOf')} ${data.title}`,
      technical: data.technical.map(({ label, value }) => ({ label: fact(label), value: fact(value) })),
    };
  }).sort((a, b) => Number(a.number) - Number(b.number));
}
