import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PlannerForm } from "@/features/planner/components/planner-form";
import { defaultLocale, locales, type Locale } from "@/i18n/routing";

type PlannerPageParams = {
  params: Promise<{ locale: string }>;
};

function isLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}

export async function generateMetadata({ params }: PlannerPageParams): Promise<Metadata> {
  const { locale: requestedLocale } = await params;
  const locale = isLocale(requestedLocale) ? requestedLocale : defaultLocale;
  const t = await getTranslations({ locale, namespace: "planner.metadata" });

  return {
    title: t("title"),
    description: t("description"),
    alternates: {
      canonical: `/${locale}/planner`,
      languages: {
        ...Object.fromEntries(
          locales.map((alternateLocale) => [alternateLocale, `/${alternateLocale}/planner`])
        ),
        "x-default": "/en/planner",
      },
    },
  };
}

export default async function PlannerPage({ params }: PlannerPageParams) {
  const { locale } = await params;
  const currentLocale = isLocale(locale) ? locale : defaultLocale;
  setRequestLocale(currentLocale);
  const t = await getTranslations("planner");

  return (
    <main
      className="flex flex-1 bg-background px-6 py-10 sm:px-8 lg:px-12"
      id="main-content"
      tabIndex={-1}
    >
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-8">
        <section className="max-w-4xl space-y-5">
          <Badge variant="outline" className="rounded-full px-3 py-1">
            {t("hero.eyebrow")}
          </Badge>
          <div className="space-y-4">
            <h1 className="text-[1.75rem] font-semibold leading-[2.125rem] tracking-tight text-balance">
              {t("hero.title")}
            </h1>
            <p className="max-w-3xl text-lg leading-8 text-muted-foreground sm:text-xl">
              {t("hero.description")}
            </p>
          </div>
        </section>

        <PlannerForm locale={currentLocale} />

        <Card className="border-dashed bg-background/80 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">{t("disclaimer.title")}</CardTitle>
            <CardDescription>{t("disclaimer.text")}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    </main>
  );
}
