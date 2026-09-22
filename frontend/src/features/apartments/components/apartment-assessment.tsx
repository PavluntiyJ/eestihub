"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { calculateBudget } from "@/lib/api";
import type { PlannerBudgetRequest, PlannerBudgetResponse } from "@/types/api";

type AmountKey = "rent" | "summer" | "winter" | "deposit" | "broker_fee" | "setup";
const FIELDS: AmountKey[] = ["rent", "summer", "winter", "deposit", "broker_fee", "setup"];
const amount = (raw: string) => raw.trim() === "" ? null : Number(raw.trim().replace(",", "."));
const valid = (raw: string) => raw.trim() === "" || (
  /^\d+(?:[.,]\d{1,2})?$/.test(raw.trim()) && Number.isFinite(amount(raw)) && amount(raw)! <= 1_000_000
);

export function ApartmentAssessment({ budgetSnapshot, budgetStale, locale }: {
  budgetSnapshot: string; budgetStale: boolean; locale: string;
}) {
  const t = useTranslations("apartment");
  const [values, setValues] = useState<Record<AmountKey, string>>({rent: "", summer: "", winter: "", deposit: "", broker_fee: "", setup: ""});
  const [basis, setBasis] = useState<"user_estimate" | "user_bill">("user_estimate");
  const [submitted, setSubmitted] = useState<{snapshot: string; response: PlannerBudgetResponse} | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const request = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const snapshot = JSON.stringify([budgetSnapshot, values, basis, budgetStale]);
  const isValid = values.rent.trim() !== "" && FIELDS.every((key) => valid(values[key]));
  const stale = budgetStale || submitted?.snapshot !== snapshot;
  const result = submitted?.response.apartment;
  const money = new Intl.NumberFormat(locale, {style: "currency", currency: "EUR"});
  const display = (value: number | null) => value === null ? t("unknown") : money.format(value);

  useEffect(() => {
    request.current++;
    controller.current?.abort();
    setLoading(false);
    setError(false);
    // This is a request generation counter, not a DOM ref. Invalidate the
    // latest request on cleanup, including unmount while a response is pending.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return () => { request.current++; controller.current?.abort(); };
  }, [snapshot]);

  async function assess(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowErrors(true);
    if (!isValid || budgetStale) {
      const key = FIELDS.find((field) => !valid(values[field]) || (field === "rent" && !values[field].trim()));
      if (key) {
        const input = event.currentTarget.querySelector<HTMLInputElement>(`#apartment-${key}`);
        const details = input?.closest("details");
        if (details) details.open = true;
        input?.focus();
      }
      return;
    }
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const id = ++request.current;
    setLoading(true);
    setError(false);
    const budget: PlannerBudgetRequest = JSON.parse(budgetSnapshot);
    const summer = amount(values.summer), winter = amount(values.winter);
    try {
      const response = await calculateBudget({...budget, apartment: {
        rent: amount(values.rent)!,
        utilities: {summer, winter, basis: summer === null && winter === null ? "unknown" : basis},
        move_in: {first_rent: amount(values.rent), deposit: amount(values.deposit), broker_fee: amount(values.broker_fee), setup: amount(values.setup)},
      }}, {signal: AbortSignal.any([abort.signal, AbortSignal.timeout(10_000)])});
      if (id === request.current) setSubmitted({snapshot, response});
    } catch {
      if (id === request.current && !abort.signal.aborted) setError(true);
    } finally {
      if (id === request.current) setLoading(false);
    }
  }

  function field(key: AmountKey) {
    const invalid = !valid(values[key]) || (key === "rent" && !values[key].trim());
    return <div className="space-y-2" key={key}>
      <label htmlFor={`apartment-${key}`} className="block text-sm font-medium">{t(`fields.${key}`)}</label>
      <input id={`apartment-${key}`} inputMode="decimal" type="text" value={values[key]}
        aria-invalid={showErrors && invalid} aria-describedby={showErrors && invalid ? `apartment-${key}-error` : undefined}
        onChange={(e) => setValues((prev) => ({...prev, [key]: e.target.value}))}
        className="h-12 w-full rounded-lg border bg-background px-3 tabular-nums focus-visible:outline-2 focus-visible:outline-ring" />
      {showErrors && invalid && <p id={`apartment-${key}-error`} className="text-sm text-destructive">{t("invalid")}</p>}
    </div>;
  }

  return <section className="space-y-6 border-t pt-8" aria-labelledby="apartment-title" data-testid="apartment-assessment">
    <div className="max-w-2xl space-y-2">
      <p className="text-sm font-semibold uppercase tracking-widest text-primary">{t("step")}</p>
      <h2 id="apartment-title" className="font-heading text-2xl font-semibold">{t("title")}</h2>
      <p className="text-muted-foreground">{t("description")}</p>
    </div>
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <form onSubmit={assess} noValidate className="space-y-5 rounded-2xl border bg-card p-5 sm:p-6">
        {field("rent")}
        <fieldset className="space-y-3">
          <legend className="mb-2 font-semibold">{t("utilities")}</legend>
          <p className="text-sm text-muted-foreground">{t("unknownHint")}</p>
          <div className="grid gap-4 sm:grid-cols-2">{field("summer")}{field("winter")}</div>
          <label className="block space-y-2 text-sm" htmlFor="apartment-basis">
            <span>{t("basis")}</span>
            <select id="apartment-basis" value={basis} onChange={(e) => setBasis(e.target.value as typeof basis)}
              className="h-12 w-full rounded-lg border bg-background px-3">
              <option value="user_estimate">{t("estimate")}</option>
              <option value="user_bill">{t("bill")}</option>
            </select>
          </label>
        </fieldset>
        <details className="rounded-xl border p-4">
          <summary className="cursor-pointer font-medium">{t("moveInTitle")}</summary>
          <p className="my-3 text-sm text-muted-foreground">{t("moveInHint")}</p>
          <div className="space-y-3">{field("deposit")}{field("broker_fee")}{field("setup")}</div>
        </details>
        {budgetStale && <p className="text-sm text-warning" role="status">{t("budgetStale")}</p>}
        {error && <p className="text-sm text-destructive" role="alert">{t("error")}</p>}
        <Button type="submit" disabled={budgetStale || loading} className="w-full sm:w-auto" data-testid="assess-apartment">
          {loading ? t("loading") : error ? t("retry") : t("calculate")}
        </Button>
      </form>
      <div className="space-y-5" aria-live="polite">
        {result ? <div className="space-y-5 rounded-2xl border border-primary/30 bg-primary/5 p-5 sm:p-6" data-testid="apartment-result">
          {stale && <p className="font-medium text-warning" data-testid="apartment-stale">{t("stale")}</p>}
          <h3 className="text-xl font-semibold">{t(`fit.${result.fit}`)}</h3>
          <p className="text-sm text-muted-foreground">{t("fitHint")}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            {(["summer", "winter"] as const).map((season) => <div key={season} className="space-y-2 rounded-xl bg-card p-4">
              <h4 className="font-medium">{t(season)}</h4>
              <p className="text-sm text-muted-foreground">{t("total")}</p>
              <p className="text-2xl font-semibold tabular-nums" data-testid={`${season}-total`}>{display(result[`${season}_total`])}</p>
              <p className="text-sm text-muted-foreground">{t("remainder")}</p>
              <p className="font-semibold tabular-nums" data-testid={`${season}-remainder`}>{display(result[`${season}_remainder`])}</p>
            </div>)}
          </div>
          {result.fit === "unknown" && <p className="text-sm">{t("incomplete")}</p>}
          {result.move_in && <div className="space-y-2 border-t pt-4">
            <h4 className="font-semibold">{t("moveInTitle")}</h4>
            <p className="text-2xl font-semibold tabular-nums" data-testid="move-in-total">{display(result.move_in.cash_needed)}</p>
            {result.move_in.cash_needed === null && <p className="text-sm">{t("subtotal", {amount: money.format(result.move_in.known_subtotal)})}</p>}
            {result.move_in.missing_components.length > 0 && <p className="text-sm text-muted-foreground">{t("missing")}: {result.move_in.missing_components.map((key) => t(`fields.${key}`)).join(", ")}</p>}
            <p className="text-sm text-muted-foreground">{t("depositHint")}</p>
          </div>}
        </div> : <div className="rounded-2xl border border-dashed p-6 text-muted-foreground">{t("empty")}</div>}
        <p className="text-sm text-muted-foreground">{t("privacy")}</p>
      </div>
    </div>
  </section>;
}
