"use client";

import { useTranslations } from "next-intl";

export default function LocaleLoading() {
  const t = useTranslations("errors");

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16" role="status">
      <span className="text-sm text-muted-foreground">{t("loading")}</span>
    </main>
  );
}
