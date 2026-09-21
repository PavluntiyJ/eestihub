import { Suspense } from "react";
import { getTranslations } from "next-intl/server";

import { LanguageSwitcher } from "@/components/language-switcher";
import { SiteNav } from "@/components/site-nav";
import { ThemeToggle } from "@/components/theme-toggle";

export async function SiteHeader() {
  const t = await getTranslations("header");
  const a11y = await getTranslations("a11y");

  return (
    <header className="border-b bg-background/80 px-6 py-4 backdrop-blur sm:px-8 lg:px-12">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
        href="#main-content"
      >
        {a11y("skipToContent")}
      </a>
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <p className="text-base font-semibold tracking-tight">{t("brand")}</p>
          <p className="text-xs text-muted-foreground">{t("tagline")}</p>
        </div>
        <div className="order-3 w-full sm:order-none sm:w-auto">
          <SiteNav />
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          {/* The switcher reads the query string so it can carry a scenario
              across locales; that keeps the pages themselves static. */}
          <Suspense
            fallback={<div className="h-8 w-[8.5rem] rounded-full border bg-background" />}
          >
            <LanguageSwitcher />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
