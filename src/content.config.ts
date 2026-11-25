import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const text = z.string().trim().min(1);

const projects = defineCollection({
  loader: glob({ pattern: '*.md', base: './src/content/projects' }),
  schema: z.object({
    number: z.string().regex(/^\d{2}$/),
    title: text,
    category: text,
    kind: z.enum(['3d', 'game', 'video', 'design']).default('3d'),
    featured: z.boolean().default(true),
    status: z.enum(['finished', 'in-progress']).default('finished'),
    image: text,
    preview: text.optional(),
    thumbnail: text.optional(),
    alt: text,
    description: text.optional(),
    model: text.optional(),
    topology: text.optional(),
    lighting: z.enum(['studio', 'night', 'soft']).default('studio'),
    exposure: z.number().positive().max(2).default(1),
    viewDirection: z.tuple([z.number(), z.number(), z.number()]).default([1, 0.7, 1]),
    overview: z.array(text).default([]),
    tools: z.array(text).default([]),
    gallery: z.array(z.object({
      src: text,
      alt: text,
      caption: text.optional(),
    })).default([]),
    technical: z.array(z.object({
      label: text,
      value: text,
    })).default([]),
  }),
});

export const collections = { projects };
