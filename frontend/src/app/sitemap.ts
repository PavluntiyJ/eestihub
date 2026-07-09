import type { MetadataRoute } from "next";

import { locales } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = ["", "/calculator", "/housing"];

  return pages.flatMap((page) =>
    locales.map((locale) => ({
      url: `${BASE_URL}/${locale}${page}`,
      alternates: {
        languages: Object.fromEntries(
          locales.map((alt) => [alt, `${BASE_URL}/${alt}${page}`])
        ),
      },
    }))
  );
}
