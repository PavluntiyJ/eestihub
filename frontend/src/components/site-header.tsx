import { getTranslations } from "next-intl/server";

import { LanguageSwitcher } from "@/components/language-switcher";
import { SiteNav } from "@/components/site-nav";

export async function SiteHeader() {
  const t = await getTranslations("header");

  return (
    <header className="border-b bg-background/80 px-6 py-4 backdrop-blur sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <p className="text-base font-semibold tracking-tight">{t("brand")}</p>
          <p className="text-xs text-muted-foreground">{t("tagline")}</p>
        </div>
        <div className="order-3 w-full sm:order-none sm:w-auto">
          <SiteNav />
        </div>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
