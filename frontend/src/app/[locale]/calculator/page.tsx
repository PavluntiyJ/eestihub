import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CalculatorForm } from "@/features/tax-calculator/components/calculator-form";
import { defaultLocale, locales, type Locale } from "@/i18n/routing";

type CalculatorPageParams = {
  params: Promise<{ locale: string }>;
};

function isLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}

export async function generateMetadata({ params }: CalculatorPageParams): Promise<Metadata> {
  const { locale: requestedLocale } = await params;
  const locale = isLocale(requestedLocale) ? requestedLocale : defaultLocale;
  const t = await getTranslations({ locale, namespace: "calculator.metadata" });

  return {
    title: t("title"),
    description: t("description"),
    alternates: {
      canonical: `/${locale}/calculator`,
      languages: {
        ...Object.fromEntries(
          locales.map((alternateLocale) => [alternateLocale, `/${alternateLocale}/calculator`])
        ),
        "x-default": "/en/calculator",
      },
    },
  };
}

export default async function CalculatorPage({ params }: CalculatorPageParams) {
  const { locale } = await params;
  const currentLocale = isLocale(locale) ? locale : defaultLocale;
  const t = await getTranslations("calculator");

  return (
    <main className="flex flex-1 bg-[radial-gradient(circle_at_top_right,var(--muted),transparent_32rem)] px-6 py-10 sm:px-8 lg:px-12">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">
        <section className="max-w-4xl space-y-5">
          <Badge variant="outline" className="rounded-full px-3 py-1">
            {t("hero.eyebrow")}
          </Badge>
          <div className="space-y-4">
            <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
              {t("hero.title")}
            </h1>
            <p className="max-w-3xl text-lg leading-8 text-muted-foreground sm:text-xl">
              {t("hero.description")}
            </p>
          </div>
        </section>

        <CalculatorForm locale={currentLocale} />

        <Card className="border-dashed bg-background/80 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">{t("disclaimer.title")}</CardTitle>
            <CardDescription>
              {t("disclaimer.text")}{" "}
              <a
                href="https://www.emta.ee"
                target="_blank"
                rel="noopener noreferrer"
                className="underline transition-colors hover:text-foreground"
              >
                EMTA
              </a>
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </main>
  );
}
