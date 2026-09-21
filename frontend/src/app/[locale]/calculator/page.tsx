import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CalculatorForm } from "@/features/tax-calculator/components/calculator-form";
import { defaultLocale, locales, type Locale } from "@/i18n/routing";
import { scenarioFromParams, parseGrossIncome } from "@/features/tax-calculator/scenario";
import type { Scenario } from "@/features/tax-calculator/scenario";
import { calculateTaxes, getHousingRents } from "@/lib/api";
import type { DistrictRent, TaxCalculationResponse } from "@/types/api";

type CalculatorPageParams = {
  params: Promise<{ locale: string }>;
};

type CalculatorPageProps = CalculatorPageParams & {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
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

// The affordability panel needs rents, but the calculator must stay usable
// (and statically rendered) when the API is down: an unreachable backend just
// hides the panel.
async function getDistricts(): Promise<DistrictRent[]> {
  try {
    const rents = await getHousingRents({ next: { revalidate: 86400 } });

    return rents.districts;
  } catch {
    return [];
  }
}

// A shared scenario link should show its numbers in the HTML, not after a
// round trip, so the calculation runs here when the URL carries one. An
// unreachable API just means the visitor starts from an empty results panel.
async function getInitialResult(
  scenario: Scenario,
  hasExplicitIncome: boolean
): Promise<TaxCalculationResponse | null> {
  if (!hasExplicitIncome) {
    return null;
  }

  try {
    return await calculateTaxes({
      gross_monthly_income: parseGrossIncome(scenario.grossMonthlyIncome),
      pension_pillar_rate: scenario.pensionPillarRate,
      equalize_by: scenario.equalizeBy,
    });
  } catch {
    return null;
  }
}

export default async function CalculatorPage({
  params,
  searchParams,
}: CalculatorPageProps) {
  const { locale } = await params;
  const currentLocale = isLocale(locale) ? locale : defaultLocale;
  setRequestLocale(currentLocale);
  const t = await getTranslations("calculator");
  const { scenario, hasExplicitIncome } = scenarioFromParams(await searchParams);
  const [districts, initialResult] = await Promise.all([
    getDistricts(),
    getInitialResult(scenario, hasExplicitIncome),
  ]);

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
            <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
              {t("hero.title")}
            </h1>
            <p className="max-w-3xl text-lg leading-8 text-muted-foreground sm:text-xl">
              {t("hero.description")}
            </p>
          </div>
        </section>

        <CalculatorForm
          districts={districts}
          initialResult={initialResult}
          initialScenario={scenario}
          locale={currentLocale}
        />

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
