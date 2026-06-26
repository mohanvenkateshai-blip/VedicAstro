import { z } from "zod";

export const birthInputSchema = z.object({
  birth_datetime: z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/, "Invalid datetime format"),
  birth_lat: z.number().min(-90).max(90),
  birth_lon: z.number().min(-180).max(180),
  birth_tz: z.number().min(-12).max(14),
  name: z.string().max(100).optional(),
  ayanamsa: z.enum(["LAHIRI"]).optional(),
});

export const muhurtaParamsSchema = z.object({
  d: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  t: z.string().regex(/^\d{2}:\d{2}$/).optional(),
  la: z.coerce.number().min(-90).max(90).optional(),
  lo: z.coerce.number().min(-180).max(180).optional(),
  tz: z.coerce.number().min(-12).max(14).optional(),
  bd: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  bt: z.string().regex(/^\d{2}:\d{2}$/).optional(),
  bl: z.coerce.number().min(-90).max(90).optional(),
  bn: z.coerce.number().min(-180).max(180).optional(),
  bz: z.coerce.number().min(-12).max(14).optional(),
});

export const envSchema = z.object({
  CVCE_BASE_URL: z.string().url().default("https://vedicastro-cvce.fly.dev"),
  DATABASE_URL: z.string().url().optional(),
  AUTH_SECRET: z.string().optional(),
  AUTH_GOOGLE_ID: z.string().optional(),
  AUTH_GOOGLE_SECRET: z.string().optional(),
  ENCRYPTION_KEY: z.string().length(32).optional(),
});

export type BirthInput = z.infer<typeof birthInputSchema>;
