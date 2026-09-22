"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Link } from "@/i18n/navigation";
import { ApiError, calculateBudget } from "@/lib/api";
import type {
  PlannerBudgetRequest,
  PlannerBudgetResponse,
  PlannerIncomeKind,
  PlannerWarningCode,
} from "@/types/api";

const MAX_MONEY = 1_000_000;
const DEFAULT_SHARE_PERCENT = "30";
// The budget call needs a bound even though the user can cancel it by
// editing: fetchJson only applies its own timeout when no signal is passed.
const REQUEST_TIMEOUT_MS = 10_000;

type PensionRate = 0 | 0.02 | 0.04 | 0.06;

const PENSION_OPTIONS: { value: PensionRate; labelKey: string }[] = [
  { value: 0, labelKey: "zero" },
  { value: 0.02, labelKey: "two" },
  { value: 0.04, labelKey: "four" },
  { value: 0.06, labelKey: "six" },
];

const INCOME_KINDS: PlannerIncomeKind[] = ["employment", "manual_net"];

function parseAmount(raw: string): number {
  return Number(raw.trim().replace(",", "."));
}

function isPresent(raw: string): boolean {
  // Number("") and Number("   ") are both 0, so blank fields must be
  // rejected before conversion: an empty input is not an explicit zero.
  return raw.trim() !== "";
}

function roundMoney(value: number): number {
  return Math.round(value * 100) / 100;
}

function roundShareFraction(value: number): number {
  // Percent input carries two decimals; the contract allows four fractional
  // digits on the share, so normalize the float division before serializing.
  return Math.round(value * 10_000) / 10_000;
}

function hasMaxDecimals(raw: string, max: number): boolean {
  const normalized = raw.trim().replace(",", ".");
  const dot = normalized.indexOf(".");

  if (dot === -1) {
    return true;
  }

  return normalized.length - dot - 1 <= max;
}

function isMoney(raw: string, minimum: number): boolean {
  const value = parseAmount(raw);

  return (
    Number.isFinite(value) &&
    value >= minimum &&
    value <= MAX_MONEY &&
    hasMaxDecimals(raw, 2)
  );
}

type PlannerFormProps = {
  locale: string;
};

// Warns before an unsaved draft is discarded: reloads and tab closes via
// beforeunload, in-app navigation (including locale switches, which remount
// this client state) via a capture-phase click guard with a native confirm.
function useUnsavedDraftWarning(active: boolean, message: string) {
  useEffect(() => {
    if (!active) {
      return;
    }

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    const onClickCapture = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest?.("a[href]");

      if (!anchor) {
        return;
      }

      const url = new URL(anchor.getAttribute("href") ?? "", window.location.href);

      if (url.origin !== window.location.origin) {
        return;
      }

      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search &&
        url.hash === window.location.hash
      ) {
        return;
      }

      if (!window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onClickCapture, true);

    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClickCapture, true);
    };
  }, [active, message]);
}

export function PlannerForm({ locale }: PlannerFormProps) {
  const t = useTranslations("planner");
  const [incomeKind, setIncomeKind] = useState<PlannerIncomeKind>("employment");
  const [grossIncome, setGrossIncome] = useState("");
  const [pensionRate, setPensionRate] = useState<"" | PensionRate>("");
  const [netIncome, setNetIncome] = useState("");
  const [spending, setSpending] = useState("");
  const [savings, setSavings] = useState("");
  const [sharePercent, setSharePercent] = useState(DEFAULT_SHARE_PERCENT);
  const [result, setResult] = useState<PlannerBudgetResponse | null>(null);
  const [submittedPayload, setSubmittedPayload] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const requestIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  const isGrossValid =
    isPresent(grossIncome) && isMoney(grossIncome, 0) && parseAmount(grossIncome) > 0;
  const isPensionValid = pensionRate !== "";
  const isNetValid = isPresent(netIncome) && isMoney(netIncome, 0);
  const isSpendingValid = isPresent(spending) && isMoney(spending, 0);
  const isSavingsValid = isPresent(savings) && isMoney(savings, 0);
  const shareValue = parseAmount(sharePercent);
  const isShareValid =
    isPresent(sharePercent) &&
    Number.isFinite(shareValue) &&
    shareValue >= 0 &&
    shareValue <= 100 &&
    hasMaxDecimals(sharePercent, 2);

  const isIncomeValid =
    incomeKind === "employment" ? isGrossValid && isPensionValid : isNetValid;
  const isFormValid = isIncomeValid && isSpendingValid && isSavingsValid && isShareValid;

  function buildPayload(): PlannerBudgetRequest {
    return {
      income:
        incomeKind === "employment"
          ? {
              kind: "employment",
              gross_monthly_income: roundMoney(parseAmount(grossIncome)),
              pension_pillar_rate: pensionRate as PensionRate,
            }
          : {
              kind: "manual_net",
              net_monthly_income: roundMoney(parseAmount(netIncome)),
            },
      monthly_non_housing: roundMoney(parseAmount(spending)),
      monthly_savings: roundMoney(parseAmount(savings)),
      housing_share: roundShareFraction(shareValue / 100),
      apartment: null,
    };
  }

  const payloadSnapshot = isFormValid ? JSON.stringify(buildPayload()) : null;
  const isStale = result !== null && submittedPayload !== null && payloadSnapshot !== submittedPayload;

  const isDirty =
    incomeKind !== "employment" ||
    grossIncome !== "" ||
    pensionRate !== "" ||
    netIncome !== "" ||
    spending !== "" ||
    savings !== "" ||
    sharePercent !== DEFAULT_SHARE_PERCENT;

  // A draft is unsaved until the user discards it, even after a fresh
  // result: leaving remounts this client state and resets the form.
  useUnsavedDraftWarning(isDirty, t("unsaved.confirm"));

  // Editing cancels the obsolete request and invalidates its late response;
  // unmounting aborts outright. Submitting never aborts: overlapping
  // requests are ordered by id instead, so a second submit can complete
  // while the first is still held.
  const inputsKey = JSON.stringify({
    incomeKind,
    grossIncome,
    pensionRate,
    netIncome,
    spending,
    savings,
    sharePercent,
  });
  const didMountRef = useRef(false);
  useEffect(() => {
    if (!didMountRef.current) {
      didMountRef.current = true;
      return;
    }

    abortRef.current?.abort();
    abortRef.current = null;
    requestIdRef.current += 1;
    setIsLoading(false);
  }, [inputsKey]);
  useEffect(() => {
    const controller = abortRef;

    return () => {
      controller.current?.abort();
    };
  }, []);

  function focusFirstInvalid() {
    const order: { id: string; valid: boolean }[] =
      incomeKind === "employment"
        ? [
            { id: "planner-gross-income", valid: isGrossValid },
            { id: "planner-pension-rate", valid: isPensionValid },
          ]
        : [{ id: "planner-net-income", valid: isNetValid }];

    order.push(
      { id: "planner-spending", valid: isSpendingValid },
      { id: "planner-savings", valid: isSavingsValid },
      { id: "planner-share", valid: isShareValid }
    );

    document.getElementById(order.find((field) => !field.valid)?.id ?? "")?.focus();
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isFormValid) {
      setShowErrors(true);
      focusFirstInvalid();
      return;
    }

    // A newer submit supersedes by id; the previous request is cancelled
    // by edits or unmount, never here, so a held first response can still
    // arrive late and must be ignored below.
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = (requestIdRef.current += 1);
    const payload = buildPayload();

    setIsLoading(true);
    setError(null);

    try {
      const response = await calculateBudget(payload, {
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]),
      });

      if (requestIdRef.current !== requestId) {
        return;
      }

      setResult(response);
      setSubmittedPayload(JSON.stringify(payload));
      setShowErrors(false);
    } catch (caughtError) {
      if (requestIdRef.current !== requestId) {
        return;
      }

      if (caughtError instanceof Error && caughtError.name === "AbortError") {
        return;
      }

      setError(caughtError instanceof ApiError ? t("errors.api") : t("errors.network"));
    } finally {
      if (requestIdRef.current === requestId) {
        setIsLoading(false);
      }
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[35rem_1fr]">
      <div className="h-fit space-y-6">
        <ol className="flex items-center gap-2 text-sm" aria-label={t("progress.budget")}>
          <ProgressStep
            current={!result}
            label={t("progress.income")}
            position={1}
          />
          <ProgressStep
            current={result !== null}
            label={t("progress.budget")}
            position={2}
          />
          <li className="flex items-center gap-2 text-muted-foreground">
            <span className="flex h-6 w-6 items-center justify-center rounded-full border text-xs">
              3
            </span>
            <span>{t("progress.explore")}</span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
              {t("progress.exploreSoon")}
            </span>
          </li>
        </ol>

        <Card className="bg-background/95 shadow-sm">
          <CardHeader>
            <CardTitle>{t("form.incomeTitle")}</CardTitle>
            <CardDescription>{t("form.incomeDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={onSubmit} ref={formRef} noValidate>
              <fieldset className="space-y-2">
                <legend className="text-sm font-medium">{t("incomeKind.label")}</legend>
                <div className="grid grid-cols-2 gap-2">
                  {INCOME_KINDS.map((kind) => (
                    <label
                      className="flex cursor-pointer items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                      key={kind}
                    >
                      <input
                        checked={incomeKind === kind}
                        name="income_kind"
                        onChange={() => setIncomeKind(kind)}
                        type="radio"
                        value={kind}
                      />
                      {t(`incomeKind.${kind === "employment" ? "employment" : "manual"}`)}
                    </label>
                  ))}
                </div>
              </fieldset>

              {incomeKind === "employment" ? (
                <>
                  <MoneyField
                    error={showErrors && !isGrossValid ? t("form.invalidGross") : null}
                    id="planner-gross-income"
                    invalid={!isGrossValid}
                    label={t("form.grossLabel")}
                    name="gross_monthly_income"
                    onChange={setGrossIncome}
                    placeholder={t("form.grossPlaceholder")}
                    value={grossIncome}
                  />
                  <div className="space-y-2">
                    <label className="text-sm font-medium" htmlFor="planner-pension-rate">
                      {t("form.pensionLabel")}
                    </label>
                    <select
                      aria-describedby={
                        showErrors && !isPensionValid ? "planner-pension-rate-error" : undefined
                      }
                      aria-invalid={!isPensionValid}
                      className="h-12 w-full rounded-lg border bg-background px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                      id="planner-pension-rate"
                      name="pension_pillar_rate"
                      onChange={(event) =>
                        setPensionRate(
                          event.target.value === ""
                            ? ""
                            : (Number(event.target.value) as PensionRate)
                        )
                      }
                      value={pensionRate}
                    >
                      <option value="">{t("form.pensionPlaceholder")}</option>
                      {PENSION_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {t(`form.pensionOptions.${option.labelKey}`)}
                        </option>
                      ))}
                    </select>
                    {showErrors && !isPensionValid ? (
                      <p
                        className="text-sm text-destructive"
                        id="planner-pension-rate-error"
                        role="alert"
                      >
                        {t("form.invalidPension")}
                      </p>
                    ) : null}
                  </div>
                </>
              ) : (
                <MoneyField
                  error={showErrors && !isNetValid ? t("form.invalidNet") : null}
                  id="planner-net-income"
                  invalid={!isNetValid}
                  label={t("form.netLabel")}
                  name="net_monthly_income"
                  onChange={setNetIncome}
                  placeholder={t("form.netPlaceholder")}
                  value={netIncome}
                />
              )}

              <div className="space-y-2 border-t pt-5">
                <h2 className="text-sm font-semibold">{t("form.budgetTitle")}</h2>
                <p className="text-sm text-muted-foreground">{t("form.budgetDescription")}</p>
              </div>

              <MoneyField
                error={showErrors && !isSpendingValid ? t("form.invalidSpending") : null}
                id="planner-spending"
                invalid={!isSpendingValid}
                label={t("form.spendingLabel")}
                name="monthly_non_housing"
                onChange={setSpending}
                placeholder="700.00"
                value={spending}
              />
              <MoneyField
                error={showErrors && !isSavingsValid ? t("form.invalidSavings") : null}
                id="planner-savings"
                invalid={!isSavingsValid}
                label={t("form.savingsLabel")}
                name="monthly_savings"
                onChange={setSavings}
                placeholder="300.00"
                value={savings}
              />
              <MoneyField
                error={showErrors && !isShareValid ? t("form.invalidShare") : null}
                id="planner-share"
                invalid={!isShareValid}
                label={t("form.shareLabel")}
                name="housing_share_percent"
                onChange={setSharePercent}
                placeholder={DEFAULT_SHARE_PERCENT}
                value={sharePercent}
              />

              <Button className="w-full" size="lg" type="submit">
                {isLoading ? t("form.loading") : t("form.submit")}
              </Button>
            </form>
          </CardContent>
        </Card>

        <details className="rounded-2xl border bg-background/80 px-4 py-3 text-sm shadow-sm">
          <summary className="cursor-pointer font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            {t("assumptions.title")}
          </summary>
          <div className="space-y-2 pt-2 text-muted-foreground">
            <p>{t("assumptions.employment")}</p>
            <p>{t("assumptions.allowance")}</p>
            <p>{t("assumptions.estimate")}</p>
          </div>
        </details>
      </div>

      <section aria-live="polite" className="space-y-6">
        {error ? (
          <Card
            className="border-destructive/30 bg-destructive/5 shadow-sm"
            data-testid="planner-error"
          >
            <CardHeader>
              <CardTitle>{t("errors.title")}</CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={() => formRef.current?.requestSubmit()}
                size="sm"
                type="button"
                variant="outline"
              >
                {t("form.retry")}
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {result ? (
          <PlannerResults
            isStale={isStale}
            locale={locale}
            result={result}
          />
        ) : (
          <Card
            className="border-dashed bg-background/80 shadow-sm"
            data-testid="planner-empty"
          >
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

function ProgressStep({
  current,
  label,
  position,
}: {
  current: boolean;
  label: string;
  position: number;
}) {
  return (
    <li className="flex items-center gap-2" aria-current={current ? "step" : undefined}>
      <span
        className={
          current
            ? "flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground"
            : "flex h-6 w-6 items-center justify-center rounded-full border text-xs text-muted-foreground"
        }
      >
        {position}
      </span>
      <span className={current ? "font-medium" : "text-muted-foreground"}>{label}</span>
    </li>
  );
}

function MoneyField({
  error,
  id,
  invalid,
  label,
  name,
  onChange,
  placeholder,
  value,
}: {
  error: string | null;
  id: string;
  invalid: boolean;
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
        aria-describedby={error ? `${id}-error` : undefined}
        aria-invalid={invalid}
        className="h-12 w-full rounded-lg border bg-background px-3 text-sm tabular-nums outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
        id={id}
        inputMode="decimal"
        name={name}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type="text"
        value={value}
      />
      {error ? (
        <p className="text-sm text-destructive" id={`${id}-error`} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

const WARNING_STYLE: Record<PlannerWarningCode, string> = {
  commitments_exceed_income: "border-warning/40 bg-warning-surface text-warning",
  utilities_incomplete: "border-warning/40 bg-warning-surface text-warning",
  move_in_incomplete: "border-warning/40 bg-warning-surface text-warning",
};

function PlannerResults({
  isStale,
  locale,
  result,
}: {
  isStale: boolean;
  locale: string;
  result: PlannerBudgetResponse;
}) {
  const t = useTranslations("planner");
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const percent = new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  const isDeficit = result.budget.available_after_commitments < 0;
  // commitments_exceed_income is covered by the deficit block above; any
  // other machine code renders from the same dictionary.
  const otherWarnings = result.warnings.filter(
    (warning) => warning.code !== "commitments_exceed_income"
  );

  return (
    <div className="space-y-6" data-testid="planner-results">
      <span className="sr-only" role="status">
        {t("results.announced")}
      </span>
      {isStale ? (
        <Card className="border-warning/40 bg-warning-surface shadow-sm" data-testid="planner-stale">
          <CardHeader>
            <CardTitle className="text-warning">{t("stale.title")}</CardTitle>
            <CardDescription className="text-warning">{t("stale.text")}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      <Card className="border-primary/30 bg-primary/5 shadow-sm">
        <CardHeader>
          <CardDescription>
            {result.income.kind === "employment"
              ? t("results.employmentKind")
              : t("results.manualKind")}
          </CardDescription>
          <CardTitle className="font-mono text-4xl font-semibold tabular-nums" data-testid="planner-allowance">
            {money.format(result.budget.housing_allowance)}
          </CardTitle>
          <CardDescription>{t("results.allowance")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border bg-background/80 p-3">
              <dt className="text-xs text-muted-foreground">{t("results.netIncome")}</dt>
              <dd className="mt-1 font-mono text-sm font-semibold tabular-nums" data-testid="planner-net">
                {money.format(result.income.net_monthly_income)}
              </dd>
            </div>
            <div className="rounded-xl border bg-background/80 p-3">
              <dt className="text-xs text-muted-foreground">{t("results.taxYear")}</dt>
              <dd className="mt-1 font-mono text-sm font-semibold tabular-nums" data-testid="planner-tax-year">
                {result.income.tax_year ?? t("results.noTaxYear")}
              </dd>
            </div>
            <div className="rounded-xl border bg-background/80 p-3">
              <dt className="text-xs text-muted-foreground">{t("results.available")}</dt>
              <dd
                className={`mt-1 font-mono text-sm font-semibold tabular-nums ${isDeficit ? "text-destructive" : ""}`}
                data-testid="planner-available"
              >
                {money.format(result.budget.available_after_commitments)}
              </dd>
            </div>
            <div className="rounded-xl border bg-background/80 p-3">
              <dt className="text-xs text-muted-foreground">{t("results.shareLimit")}</dt>
              <dd className="mt-1 font-mono text-sm font-semibold tabular-nums" data-testid="planner-share-limit">
                {money.format(result.budget.share_limit)} ·{" "}
                {percent.format(result.budget.housing_share)}
              </dd>
            </div>
          </dl>

          {isDeficit ? (
            <div
              className="rounded-xl border border-destructive/50 bg-destructive/5 p-3"
              data-testid="planner-deficit"
            >
              <p className="text-sm font-medium text-destructive">{t("results.deficitTitle")}</p>
              <p className="mt-1 text-sm text-destructive">{t("results.warnings.commitments_exceed_income")}</p>
            </div>
          ) : null}

          {otherWarnings.length > 0 ? (
            <ul className="space-y-2">
              {otherWarnings.map((warning) => (
                <li
                  className={`rounded-lg border px-3 py-2 text-sm ${WARNING_STYLE[warning.code]}`}
                  key={warning.code}
                >
                  {t(`results.warnings.${warning.code}`)}
                </li>
              ))}
            </ul>
          ) : null}

          <div className="space-y-1 border-t pt-3 text-sm">
            <Link
              className="font-medium text-primary underline underline-offset-4 hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              href="/housing"
            >
              {t("results.housingContext")}
            </Link>
            <p className="text-muted-foreground">{t("results.housingNote")}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
