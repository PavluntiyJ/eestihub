"use client";

import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LocaleNotFound() {
  const t = useTranslations("errors");

  return (
    <main className="flex flex-1 items-center px-6 py-16 sm:px-8 lg:px-12">
      <Card className="mx-auto w-full max-w-xl bg-background/95 shadow-sm">
        <CardHeader className="space-y-4">
          <div className="space-y-2">
            <CardTitle>{t("notFound.title")}</CardTitle>
            <CardDescription>{t("notFound.description")}</CardDescription>
          </div>
          <div>
            <Link
              className="text-sm font-medium underline underline-offset-4 transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              href="/"
            >
              {t("notFound.home")}
            </Link>
          </div>
        </CardHeader>
      </Card>
    </main>
  );
}
