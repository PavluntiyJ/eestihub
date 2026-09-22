import type { MetadataRoute } from "next";

import { locales } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const LAST_MODIFIED = new Date("2026-09-02");

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = ["", "/planner", "/calculator", "/housing", "/eresidency"];

  return pages.flatMap((page) =>
    locales.map((locale) => ({
      url: `${BASE_URL}/${locale}${page}`,
      lastModified: LAST_MODIFIED,
      alternates: {
        languages: {
          ...Object.fromEntries(
            locales.map((alt) => [alt, `${BASE_URL}/${alt}${page}`])
          ),
          "x-default": `${BASE_URL}/en${page}`,
        },
      },
    }))
  );
}
