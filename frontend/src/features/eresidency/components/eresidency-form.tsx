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
import { ApiError, calculateEResidency } from "@/lib/api";
import type { EResidencyCalculationResponse } from "@/types/api";

type EResidencyFormProps = {
  locale: string;
};

export function EResidencyForm({ locale }: EResidencyFormProps) {
  const t = useTranslations("eresidency");
  const [monthlyRevenue, setMonthlyRevenue] = useState("3000");
  const [accountingFee, setAccountingFee] = useState("75");
  const [result, setResult] = useState<EResidencyCalculationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const monthlyRevenueValue = parseAmount(monthlyRevenue);
  const accountingFeeValue = parseAmount(accountingFee);
  const isRevenueValid = Number.isFinite(monthlyRevenueValue) && monthlyRevenueValue > 0;
  const isAccountingValid = Number.isFinite(accountingFeeValue) && accountingFeeValue >= 0;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isRevenueValid || !isAccountingValid) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      setResult(
        await calculateEResidency({
          expected_monthly_revenue: monthlyRevenueValue,
          monthly_accounting_fee: accountingFeeValue,
        })
      );
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
            <AmountField
              error={!isRevenueValid ? t("form.invalidRevenue") : null}
              id="expected-monthly-revenue"
              label={t("form.revenueLabel")}
              name="expected_monthly_revenue"
              onChange={setMonthlyRevenue}
              placeholder={t("form.revenuePlaceholder")}
              value={monthlyRevenue}
            />
            <AmountField
              error={!isAccountingValid ? t("form.invalidAccounting") : null}
              id="monthly-accounting-fee"
              label={t("form.accountingLabel")}
              name="monthly_accounting_fee"
              onChange={setAccountingFee}
              placeholder={t("form.accountingPlaceholder")}
              value={accountingFee}
            />
            <Button
              className="w-full"
              disabled={!isRevenueValid || !isAccountingValid || isLoading}
              size="lg"
              type="submit"
            >
              {isLoading ? t("form.loading") : t("form.submit")}
            </Button>
          </form>
        </CardContent>
      </Card>

      <section aria-live="polite" className="space-y-6">
        {error ? (
          <Card className="border-destructive/30 bg-destructive/5 shadow-sm">
            <CardHeader>
              <CardTitle>{t("errors.title")}</CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        {result ? (
          <EResidencyResults locale={locale} result={result} />
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

function AmountField({
  error,
  id,
  label,
  name,
  onChange,
  placeholder,
  value,
}: {
  error: string | null;
  id: string;
  label: string;
  name: string;
  onChange: (value: string) => void;
  placeholder: string;
  value: string;
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium" htmlFor={id}>
        {label}
      </label>
      <input
        className="h-10 w-full rounded-lg border bg-background px-3 text-sm tabular-nums outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        id={id}
        inputMode="decimal"
        name={name}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type="text"
        value={value}
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}

function EResidencyResults({
  locale,
  result,
}: {
  locale: string;
  result: EResidencyCalculationResponse;
}) {
  const t = useTranslations("eresidency");
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          label={t("results.firstYearTotal")}
          testId="first-year-total"
          value={money.format(result.first_year_total_cost)}
        />
        <MetricCard
          label={t("results.monthlyRunning")}
          value={money.format(result.monthly_running_cost)}
        />
        <MetricCard
          label={t("results.breakEven")}
          value={money.format(result.break_even_monthly_revenue)}
        />
        <MetricCard
          label={t("results.firstYearRevenue")}
          value={money.format(result.first_year_revenue)}
        />
        <MetricCard
          label={t("results.firstYearSurplus")}
          value={money.format(result.first_year_surplus)}
        />
      </div>

      <Card className="bg-background/95 shadow-sm">
        <CardHeader>
          <CardTitle>{t("setup.title")}</CardTitle>
          <CardDescription>{t("setup.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {result.setup_breakdown.map((line) => (
            <div
              className="flex items-center justify-between gap-4 border-b pb-3 last:border-0 last:pb-0"
              key={line.name}
            >
              <span className="text-sm text-muted-foreground">
                {t(`setup.items.${line.name}`)}
              </span>
              <span className="font-mono text-sm tabular-nums">{money.format(line.amount)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({
  label,
  testId,
  value,
}: {
  label: string;
  testId?: string;
  value: string;
}) {
  return (
    <Card className="bg-background/95 shadow-sm">
      <CardHeader className="gap-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-mono text-2xl tabular-nums" data-testid={testId}>
          {value}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}

function parseAmount(value: string): number {
  return Number(value.trim().replace(",", "."));
}
