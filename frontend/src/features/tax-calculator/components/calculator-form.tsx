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
import { AffordabilityPanel } from "@/features/tax-calculator/components/affordability-panel";
import {
  isGrossIncomeValid as isValidIncome,
  parseGrossIncome,
  scenarioToQuery,
  type PensionPillarRate,
  type Scenario,
} from "@/features/tax-calculator/scenario";
import type {
  ConstraintSeverity,
  DistrictRent,
  EqualizeBy,
  RegimeResult,
  TaxCalculationResponse,
} from "@/types/api";

const PENSION_PILLAR_OPTIONS: { value: PensionPillarRate; labelKey: string }[] = [
  { value: 0, labelKey: "zero" },
  { value: 0.02, labelKey: "two" },
  { value: 0.04, labelKey: "four" },
  { value: 0.06, labelKey: "six" },
];

const COMPARISON_BASIS_OPTIONS: EqualizeBy[] = ["gross", "payer_cost"];
const CONSTRAINT_STYLES: Record<ConstraintSeverity, string> = {
  info: "border-primary/30 bg-primary/10 text-foreground",
  warning: "border-warning/40 bg-warning-surface text-warning",
  blocker:
    "border-destructive/50 bg-destructive/10 text-destructive dark:border-destructive/70",
};

type CalculatorFormProps = {
  districts: DistrictRent[];
  initialResult: TaxCalculationResponse | null;
  initialScenario: Scenario;
  locale: string;
};

export function CalculatorForm({
  districts,
  initialResult,
  initialScenario,
  locale,
}: CalculatorFormProps) {
  const t = useTranslations("calculator");
  const [grossIncome, setGrossIncome] = useState(initialScenario.grossMonthlyIncome);
  const [pensionPillarRate, setPensionPillarRate] = useState<PensionPillarRate>(
    initialScenario.pensionPillarRate
  );
  const [equalizeBy, setEqualizeBy] = useState<EqualizeBy>(initialScenario.equalizeBy);
  const [result, setResult] = useState<TaxCalculationResponse | null>(initialResult);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLinkCopied, setIsLinkCopied] = useState(false);
  const grossIncomeValue = parseGrossIncome(grossIncome);
  const isGrossIncomeValid = isValidIncome(grossIncome);


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
        equalize_by: equalizeBy,
      });
      setResult(response);
      setIsLinkCopied(false);

      // The form owns its state after mount, so the scenario is written with
      // the native history API: it updates the address bar and
      // useSearchParams without an RSC round trip. router.replace would fetch
      // the scenario URL from the server, and that request can be aborted by
      // a concurrent link prefetch, leaving the address bar stale.
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}?${scenarioToQuery({
          grossMonthlyIncome: grossIncome,
          pensionPillarRate,
          equalizeBy,
        })}`
      );
    } catch (caughtError) {
      setResult(null);
      setError(caughtError instanceof ApiError ? t("errors.api") : t("errors.network"));
    } finally {
      setIsLoading(false);
    }
  }

  async function onCopyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setIsLinkCopied(true);
    } catch {
      setIsLinkCopied(false);
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
                {equalizeBy === "gross"
                  ? t("form.grossIncomeLabel")
                  : t("form.payerCostLabel")}
              </label>
              <input
                id="gross-monthly-income"
                aria-describedby={
                  isGrossIncomeValid ? undefined : "gross-monthly-income-error"
                }
                aria-invalid={!isGrossIncomeValid}
                className="h-12 w-full rounded-lg border bg-background px-3 text-sm tabular-nums outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                inputMode="decimal"
                min="0.01"
                name="gross_monthly_income"
                onChange={(event) => setGrossIncome(event.target.value)}
                placeholder={t("form.grossIncomePlaceholder")}
                step="0.01"
                type="text"
                value={grossIncome}
              />
              {!isGrossIncomeValid ? (
                <p className="text-sm text-destructive" id="gross-monthly-income-error" role="alert">
                  {t("form.invalidIncome")}
                </p>
              ) : null}
            </div>

            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">{t("basis.label")}</legend>
              <div className="grid grid-cols-2 gap-2">
                {COMPARISON_BASIS_OPTIONS.map((basis) => (
                  <label
                    className="flex cursor-pointer items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                    key={basis}
                  >
                    <input
                      checked={equalizeBy === basis}
                      name="equalize_by"
                      onChange={() => setEqualizeBy(basis)}
                      type="radio"
                      value={basis}
                    />
                    {t(`basis.options.${basis}`)}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="pension-pillar-rate">
                {t("form.pensionPillarLabel")}
              </label>
              <select
                id="pension-pillar-rate"
                className="h-12 w-full rounded-lg border bg-background px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
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
          <>
            <div className="flex justify-end">
              <Button
                onClick={onCopyLink}
                size="sm"
                type="button"
                variant="outline"
              >
                {isLinkCopied ? t("share.copied") : t("share.copy")}
              </Button>
            </div>
            <ResultsView
              districts={districts}
              equalizeBy={result.input.equalize_by}
              locale={locale}
              results={result.results}
            />
          </>
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

function ResultsView({
  districts,
  equalizeBy,
  locale,
  results,
}: {
  districts: DistrictRent[];
  equalizeBy: EqualizeBy;
  locale: string;
  results: RegimeResult[];
}) {
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
          <CardDescription>
            {t("comparison.description")} {t("comparison.activeBasis", {
              basis: t(`basis.options.${equalizeBy}`),
            })}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {sortedResults.map((result) => {
            const widthPercentage =
              bestNetIncome > 0
                ? Math.max(0, Math.min(100, (result.net_income / bestNetIncome) * 100))
                : 0;
            const isNegative = result.net_income < 0;

            return (
              <div
                key={result.regime}
                className="space-y-2"
                data-regime-comparison={result.regime}
              >
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{t(`regime.${result.regime}`)}</span>
                  <span
                    className={`font-mono tabular-nums ${isNegative ? "font-semibold text-destructive" : ""}`}
                  >
                    {moneyFormatter.format(result.net_income)}
                  </span>
                </div>
                <div
                  className={`relative h-3 overflow-hidden rounded-full ${isNegative ? "bg-destructive/15" : "bg-muted"}`}
                >
                  <div
                    className="h-full rounded-full bg-primary"
                    data-net-bar-fill
                    style={{ width: `${widthPercentage}%` }}
                  />
                  {isNegative ? (
                    <div
                      aria-hidden="true"
                      className="absolute inset-y-0 left-0 w-1 bg-destructive"
                    />
                  ) : null}
                </div>
                {isNegative ? (
                  <p className="text-xs font-medium text-destructive">
                    {t("results.negativeNet")}
                  </p>
                ) : null}
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        {sortedResults.map((result, index) => (
          <Card
            key={result.regime}
            className={
              result.net_income < 0
                ? "border-destructive/50 bg-destructive/5 shadow-sm"
                : "bg-background/95 shadow-sm"
            }
            data-regime={result.regime}
          >
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-3">
                <span>{t(`regime.${result.regime}`)}</span>
                {index === 0 ? (
                  <span className="rounded-full bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground">
                    {t("results.best")}
                  </span>
                ) : result.net_income < 0 ? (
                  <span className="rounded-full bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive">
                    {t("results.negativeNet")}
                  </span>
                ) : null}
              </CardTitle>
              <CardDescription>{t("results.cardDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div
                className={`grid gap-3 ${result.net_income < 0 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}
              >
                <Metric label={t("results.netIncome")} value={moneyFormatter.format(result.net_income)} />
                <Metric
                  label={t("results.employerTotalCost")}
                  value={moneyFormatter.format(result.employer_total_cost)}
                />
                {result.net_income >= 0 ? (
                  <Metric
                    label={t("results.effectiveTaxRate")}
                    value={percentFormatter.format(result.effective_tax_rate)}
                  />
                ) : null}
              </div>

              {result.constraints.length > 0 ? (
                <ul className="space-y-2">
                  {result.constraints.map((constraint) => (
                    <li
                      className={`rounded-lg border px-3 py-2 text-sm ${CONSTRAINT_STYLES[constraint.severity]}`}
                      key={constraint.code}
                    >
                      {t(`constraints.${constraint.code}`)}
                    </li>
                  ))}
                </ul>
              ) : null}

              <div className="space-y-2">
                <h2 className="text-sm font-medium">{t("breakdown.title")}</h2>
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

      {districts.length > 0 && sortedResults[0] ? (
        <AffordabilityPanel
          districts={districts}
          locale={locale}
          topResult={sortedResults[0]}
        />
      ) : null}
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
