"use client";

import { useTranslations } from "next-intl";

export default function LocaleLoading() {
  const t = useTranslations("errors");

  return (
    <main
      className="flex flex-1 items-center justify-center px-6 py-16"
      id="main-content"
      tabIndex={-1}
    >
      <span aria-live="polite" className="text-sm text-muted-foreground" role="status">
        {t("loading")}
      </span>
    </main>
  );
}
