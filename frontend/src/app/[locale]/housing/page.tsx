import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RentBarChart } from "@/features/housing/components/rent-bar-chart";
import { RentTable } from "@/features/housing/components/rent-table";
import { defaultLocale, locales, type Locale } from "@/i18n/routing";
import { getHousingRents } from "@/lib/api";
import type { HousingRentsResponse } from "@/types/api";

export const dynamic = "force-dynamic";

type HousingPageParams = {
  params: Promise<{ locale: string }>;
};

function isLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}

async function getRentData(): Promise<HousingRentsResponse | null> {
  try {
    return await getHousingRents({ cache: "no-store" });
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: HousingPageParams): Promise<Metadata> {
  const { locale: requestedLocale } = await params;
  const locale = isLocale(requestedLocale) ? requestedLocale : defaultLocale;
  const t = await getTranslations({ locale, namespace: "housing.metadata" });

  return {
    title: t("title"),
    description: t("description"),
    alternates: {
      canonical: `/${locale}/housing`,
      languages: Object.fromEntries(
        locales.map((alternateLocale) => [alternateLocale, `/${alternateLocale}/housing`])
      ),
    },
  };
}

export default async function HousingPage({ params }: HousingPageParams) {
  const { locale } = await params;
  const currentLocale = isLocale(locale) ? locale : defaultLocale;
  const t = await getTranslations("housing");
  const rentData = await getRentData();
  const moneyFormatter = new Intl.NumberFormat(currentLocale, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  });
  const formatCurrency = (value: number) => moneyFormatter.format(value);

  return (
    <main className="flex flex-1 bg-[linear-gradient(135deg,var(--background),var(--muted)_52%,var(--background))] px-6 py-10 sm:px-8 lg:px-12">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">
        <section className="grid gap-6 lg:grid-cols-[1fr_22rem] lg:items-end">
          <div className="space-y-5">
            <Badge variant="outline" className="rounded-full px-3 py-1">
              {t("hero.eyebrow")}
            </Badge>
            <div className="space-y-4">
              <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
                {t("hero.title")}
              </h1>
              <p className="max-w-3xl text-lg leading-8 text-muted-foreground sm:text-xl">
                {t("hero.description")}
              </p>
            </div>
          </div>
          <Card className="border-border/70 bg-background/90 shadow-sm">
            <CardHeader>
              <CardTitle>{t("summary.title")}</CardTitle>
              <CardDescription>
                {rentData ? t("summary.updated", { date: rentData.updated_at }) : t("states.unavailable")}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl border bg-muted/40 p-4">
                <div className="text-muted-foreground">{t("summary.city")}</div>
                <div className="mt-1 font-semibold">{rentData?.city ?? "Tallinn"}</div>
              </div>
              <div className="rounded-xl border bg-muted/40 p-4">
                <div className="text-muted-foreground">{t("summary.districts")}</div>
                <div className="mt-1 font-semibold">{rentData?.districts.length ?? 0}</div>
              </div>
            </CardContent>
          </Card>
        </section>

        {rentData ? (
          <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <Card className="bg-background/95 shadow-sm">
              <CardHeader>
                <CardTitle>{t("chart.title")}</CardTitle>
                <CardDescription>{t("chart.description")}</CardDescription>
              </CardHeader>
              <CardContent>
                <RentBarChart districts={rentData.districts} label={t("chart.valueLabel")} />
              </CardContent>
            </Card>

            <Card className="bg-background/95 shadow-sm">
              <CardHeader>
                <CardTitle>{t("table.title")}</CardTitle>
                <CardDescription>{t("table.description")}</CardDescription>
              </CardHeader>
              <CardContent>
                <RentTable
                  districts={rentData.districts}
                  labels={{
                    district: t("table.columns.district"),
                    oneRoom: t("table.columns.oneRoom"),
                    twoRoom: t("table.columns.twoRoom"),
                    threeRoom: t("table.columns.threeRoom"),
                    utilities: t("table.columns.utilities"),
                  }}
                  formatCurrency={formatCurrency}
                />
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card className="border-dashed bg-background/90 shadow-sm">
            <CardHeader>
              <CardTitle>{t("states.unavailableTitle")}</CardTitle>
              <CardDescription>{t("states.unavailableDescription")}</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </main>
  );
}
