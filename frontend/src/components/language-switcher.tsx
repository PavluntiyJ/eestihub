"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

import { Link, usePathname } from "@/i18n/navigation";
import { locales, type Locale } from "@/i18n/routing";

export function LanguageSwitcher() {
  const t = useTranslations("languageSwitcher");
  const activeLocale = useLocale() as Locale;
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  // The hash never reaches the server, so it can only be picked up after mount.
  const [hash, setHash] = useState("");

  useEffect(() => {
    setHash(window.location.hash);
  }, [pathname, query]);

  const href = `${pathname}${query ? `?${query}` : ""}${hash}`;

  return (
    <nav aria-label={t("label")} className="flex items-center gap-1 rounded-full border bg-background p-1">
      {locales.map((locale) => {
        const isActive = locale === activeLocale;

        return (
          <Link
            key={locale}
            href={href}
            locale={locale}
            aria-current={isActive ? "page" : undefined}
            className={
              isActive
                ? "rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground"
                : "rounded-full px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            }
          >
            {t(`locales.${locale}`)}
          </Link>
        );
      })}
    </nav>
  );
}
