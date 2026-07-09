import { getTranslations } from "next-intl/server";

import { LanguageSwitcher } from "@/components/language-switcher";

export async function SiteHeader() {
  const t = await getTranslations("header");

  return (
    <header className="border-b bg-background/80 px-6 py-4 backdrop-blur sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <div>
          <p className="text-base font-semibold tracking-tight">{t("brand")}</p>
          <p className="text-xs text-muted-foreground">{t("tagline")}</p>
        </div>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
