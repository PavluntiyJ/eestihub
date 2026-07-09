export const locales = ["en", "et", "ru"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const routing = {
  locales,
  defaultLocale,
};
