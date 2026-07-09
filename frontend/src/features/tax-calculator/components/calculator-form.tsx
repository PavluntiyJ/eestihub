"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, calculateTaxes } from "@/lib/api";
import type { RegimeResult, TaxCalculationResponse, TaxCalculationRequest } from "@/types/api";

type PensionPillarRate = TaxCalculationRequest["pension_pillar_rate"];

const PENSION_PILLAR_OPTIONS: { value: PensionPillarRate; labelKey: string }[] = [
  { value: 0, labelKey: "zero" },
  { value: 0.02, labelKey: "two" },
  { value: 0.04, labelKey: "four" },
  { value: 0.06, labelKey: "six" },
];

type CalculatorFormProps = {
  locale: string;
};

export function CalculatorForm({ locale }: CalculatorFormProps) {
  const t = useTranslations("calculator");
  const [grossIncome, setGrossIncome] = useState("3000");
  const [pensionPillarRate, setPensionPillarRate] = useState<PensionPillarRate>(0.02);
  const [result, setResult] = useState<TaxCalculationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const grossIncomeValue = Number(grossIncome);
  const isGrossIncomeValid = Number.isFinite(grossIncomeValue) && grossIncomeValue > 0;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isGrossIncomeValid) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await calculateTaxes({
        gross_monthly_income: grossIncomeValue,
        pension_pillar_rate: pensionPillarRate,
      });
      setResult(response);
    } catch (caughtError) {
      setResult(null);
      setError(caughtError instanceof ApiError ? t("errors.api") : t("errors.network"));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[24rem_1fr]">
      <Card className="h-fit bg-background/95 shadow-sm">
        <CardHeader>
          <CardTitle>{t("form.title")}</CardTitle>
          <CardDescription>{t("form.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={onSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="gross-monthly-income">
                {t("form.grossIncomeLabel")}
              </label>
              <input
                id="gross-monthly-income"
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm tabular-nums outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                inputMode="decimal"
                min="0.01"
                name="gross_monthly_income"
                onChange={(event) => setGrossIncome(event.target.value)}
                placeholder={t("form.grossIncomePlaceholder")}
                step="0.01"
                type="number"
                value={grossIncome}
              />
              {!isGrossIncomeValid ? (
                <p className="text-sm text-destructive">{t("form.invalidIncome")}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pension-pillar-rate">
                {t("form.pensionPillarLabel")}
              </label>
              <select
                id="pension-pillar-rate"
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                name="pension_pillar_rate"
                onChange={(event) => setPensionPillarRate(Number(event.target.value) as PensionPillarRate)}
                value={pensionPillarRate}
              >
                {PENSION_PILLAR_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {t(`form.pensionOptions.${option.labelKey}`)}
                  </option>
                ))}
              </select>
            </div>

            <Button className="w-full" disabled={!isGrossIncomeValid || isLoading} size="lg" type="submit">
              {isLoading ? t("form.loading") : t("form.submit")}
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-6" aria-live="polite">
        {error ? (
          <Card className="border-destructive/30 bg-destructive/5 shadow-sm">
            <CardHeader>
              <CardTitle>{t("errors.title")}</CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        {result ? (
          <ResultsView locale={locale} results={result.results} />
        ) : (
          <Card className="border-dashed bg-background/80 shadow-sm">
            <CardHeader>
              <CardTitle>{t("empty.title")}</CardTitle>
              <CardDescription>{t("empty.description")}</CardDescription>
            </CardHeader>
          </Card>
        )}
      </section>
    </div>
  );
}

function ResultsView({ locale, results }: { locale: string; results: RegimeResult[] }) {
  const t = useTranslations("calculator");
  const moneyFormatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const percentFormatter = new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const sortedResults = [...results].sort((left, right) => right.net_income - left.net_income);
  const bestNetIncome = sortedResults[0]?.net_income ?? 0;

  return (
    <div className="space-y-6">
      <Card className="bg-background/95 shadow-sm">
        <CardHeader>
          <CardTitle>{t("comparison.title")}</CardTitle>
          <CardDescription>{t("comparison.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {sortedResults.map((result) => {
            const width = bestNetIncome > 0 ? `${(result.net_income / bestNetIncome) * 100}%` : "0%";

            return (
              <div key={result.regime} className="space-y-2">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{t(`regime.${result.regime}`)}</span>
                  <span className="font-mono tabular-nums">{moneyFormatter.format(result.net_income)}</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width }} />
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        {sortedResults.map((result, index) => (
          <Card key={result.regime} className="bg-background/95 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-3">
                <span>{t(`regime.${result.regime}`)}</span>
                {index === 0 ? (
                  <span className="rounded-full bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground">
                    {t("results.best")}
                  </span>
                ) : null}
              </CardTitle>
              <CardDescription>{t("results.cardDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric label={t("results.netIncome")} value={moneyFormatter.format(result.net_income)} />
                <Metric
                  label={t("results.employerTotalCost")}
                  value={moneyFormatter.format(result.employer_total_cost)}
                />
                <Metric
                  label={t("results.effectiveTaxRate")}
                  value={percentFormatter.format(result.effective_tax_rate)}
                />
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-medium">{t("breakdown.title")}</h3>
                <div className="divide-y rounded-lg border">
                  {result.breakdown.map((line) => (
                    <div className="flex items-center justify-between gap-3 px-3 py-2 text-sm" key={line.name}>
                      <span className="text-muted-foreground">{t(`breakdown.${line.name}`)}</span>
                      <span className="font-mono tabular-nums">{moneyFormatter.format(line.amount)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-muted/30 p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-sm font-semibold tabular-nums">{value}</div>
    </div>
  );
}
