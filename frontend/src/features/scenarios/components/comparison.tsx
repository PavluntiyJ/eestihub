"use client";
import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { calculateBudget } from "@/lib/api";
import type { PlannerApartmentResult } from "@/types/api";
import {
  useWorkspace,
  getWorkspace,
  updateWorkspace,
  type Candidate,
  type CandidateDraft as Draft,
} from "../store";
import { ScenarioControls } from "./scenario-controls";

const keys = [
  "rent",
  "summer",
  "winter",
  "first_rent",
  "deposit",
  "broker_fee",
  "setup",
] as const;
const valid = (v: string) =>
  v === "" ||
  (/^\d+(?:[.,]\d{1,2})?$/.test(v) && Number(v.replace(",", ".")) <= 1000000);
const amount = (v: string) => (v === "" ? null : Number(v.replace(",", ".")));

export function Comparison({ locale }: { locale: string }) {
  const t = useTranslations("compare"),
    a = useTranslations("apartment"),
    explore = useTranslations("explore");
  const state = useWorkspace();
  const [editing, setEditing] = useState<Draft | null>(
    getWorkspace().candidateDraft,
  );
  const [invalid, setInvalid] = useState(false);
  const [results, setResults] = useState<
    Record<string, PlannerApartmentResult>
  >({});
  const [error, setError] = useState(false),
    [retry, setRetry] = useState(0);
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
  });
  const display = (v: number | null) =>
    v === null ? a("unknown") : money.format(v);
  useEffect(() => {
    updateWorkspace({ candidateDraft: editing });
  }, [editing]);
  useEffect(() => {
    const abort = new AbortController();
    setResults({});
    setError(false);
    if (!state.budget || !state.candidates.length) return () => abort.abort();
    const budget = state.budget;
    Promise.all(
      state.candidates.map(
        async (c) =>
          [
            c.id,
            (
              await calculateBudget(
                { ...budget, apartment: c.costs },
                {
                  signal: AbortSignal.any([
                    abort.signal,
                    AbortSignal.timeout(10000),
                  ]),
                },
              )
            ).apartment!,
          ] as const,
      ),
    )
      .then((rows) => {
        if (!abort.signal.aborted) setResults(Object.fromEntries(rows));
      })
      .catch(() => {
        if (!abort.signal.aborted) setError(true);
      });
    return () => abort.abort();
  }, [state.budget, state.candidates, retry]);
  function edit(candidate?: Candidate) {
    setInvalid(false);
    setEditing({
      id: candidate?.id || crypto.randomUUID(),
      name: candidate?.name || "",
      address: candidate?.address || "",
      basis:
        candidate?.costs.utilities.basis === "legacy_assumption"
          ? "legacy_assumption"
          : candidate?.costs.utilities.basis === "user_bill"
            ? "user_bill"
            : "user_estimate",
      values: {
        rent: candidate ? String(candidate.costs.rent) : "",
        summer: candidate?.costs.utilities.summer?.toString() || "",
        winter: candidate?.costs.utilities.winter?.toString() || "",
        first_rent: candidate?.costs.move_in?.first_rent?.toString() || "",
        deposit: candidate?.costs.move_in?.deposit?.toString() || "",
        broker_fee: candidate?.costs.move_in?.broker_fee?.toString() || "",
        setup: candidate?.costs.move_in?.setup?.toString() || "",
      },
    });
  }
  function save(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    if (
      !editing.name.trim() ||
      /[<>\x00-\x1f]/.test(editing.name + editing.address) ||
      !editing.values.rent ||
      !keys.every((k) => valid(editing.values[k]))
    ) {
      setInvalid(true);
      return;
    }
    const v = editing.values;
    const candidate: Candidate = {
      id: editing.id,
      name: editing.name.trim(),
      address: editing.address.trim() || null,
      costs: {
        rent: amount(v.rent)!,
        utilities: {
          summer: amount(v.summer),
          winter: amount(v.winter),
          basis: v.summer === "" && v.winter === "" ? "unknown" : editing.basis,
        },
        move_in: {
          first_rent: amount(v.first_rent),
          deposit: amount(v.deposit),
          broker_fee: amount(v.broker_fee),
          setup: amount(v.setup),
        },
      },
    };
    const previous = state.candidates.find((c) => c.id === candidate.id);
    if (previous?.costs.rent === candidate.costs.rent)
      candidate.origin = previous.origin;
    const exists = !!previous;
    if (!exists && state.candidates.length >= 3) return;
    updateWorkspace({
      candidates: exists
        ? state.candidates.map((c) => (c.id === candidate.id ? candidate : c))
        : [...state.candidates, candidate],
    });
    setEditing(null);
  }
  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-primary/10 p-5">
        <div>
          <p className="font-semibold">
            {state.result
              ? t("allowance", {
                  amount: money.format(state.result.budget.housing_allowance),
                })
              : t("noBudget")}
          </p>
          <p className="mt-1 text-sm">{t("sameBudget")}</p>
        </div>
        <Link href="/planner" className="font-medium underline">
          {t("editBudget")}
        </Link>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <Button
          disabled={state.candidates.length >= 3 || !!editing}
          onClick={() => edit()}
        >
          {t("add")}
        </Button>
        <Link href="/explore" className="underline">
          {t("explore")}
        </Link>
        <p className="text-sm text-muted-foreground">
          {t("count", { count: state.candidates.length })}
        </p>
      </div>
      {editing && (
        <form
          onSubmit={save}
          className="space-y-4 rounded-2xl border border-primary bg-card p-5"
          data-testid="candidate-editor"
        >
          <h2 className="text-xl font-semibold">{t("editor")}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-sm">
              <span className="block">{t("name")}</span>
              <input
                autoFocus
                required
                maxLength={80}
                value={editing.name}
                onChange={(e) =>
                  setEditing({ ...editing, name: e.target.value })
                }
                className="h-12 w-full rounded-lg border bg-background px-3"
              />
            </label>
            <label className="space-y-2 text-sm">
              <span className="block">{t("address")}</span>
              <input
                maxLength={200}
                value={editing.address}
                onChange={(e) =>
                  setEditing({ ...editing, address: e.target.value })
                }
                className="h-12 w-full rounded-lg border bg-background px-3"
              />
            </label>
            {keys.map((key) => (
              <label key={key} className="space-y-2 text-sm">
                <span className="block">{a(`fields.${key}`)}</span>
                <input
                  inputMode="decimal"
                  required={key === "rent"}
                  value={editing.values[key]}
                  aria-invalid={
                    invalid &&
                    (!valid(editing.values[key]) ||
                      (key === "rent" && !editing.values[key]))
                  }
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      values: { ...editing.values, [key]: e.target.value },
                    })
                  }
                  className="h-12 w-full rounded-lg border bg-background px-3"
                />
              </label>
            ))}
            <label className="space-y-2 text-sm">
              <span className="block">{a("basis")}</span>
              <select
                value={editing.basis}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    basis: e.target.value as Draft["basis"],
                  })
                }
                className="h-12 w-full rounded-lg border bg-background px-3"
              >
                <option value="user_estimate">{a("estimate")}</option>
                <option value="user_bill">{a("bill")}</option>
                {editing.basis === "legacy_assumption" && (
                  <option value="legacy_assumption">{t("legacy")}</option>
                )}
              </select>
            </label>
          </div>
          <p className="text-sm text-muted-foreground">
            {a("unknownHint")} {a("depositHint")}
          </p>
          {invalid && <p role="alert">{a("invalid")}</p>}
          <Button type="submit">{t("confirm")}</Button>{" "}
          <Button
            type="button"
            variant="outline"
            onClick={() => setEditing(null)}
          >
            {t("cancel")}
          </Button>
        </form>
      )}
      {error && (
        <p role="alert">
          {a("error")}{" "}
          <button className="underline" onClick={() => setRetry((n) => n + 1)}>
            {a("retry")}
          </button>
        </p>
      )}
      {state.candidates.length === 0 && (
        <p className="rounded-2xl border border-dashed p-8 text-muted-foreground">
          {t("empty")}
        </p>
      )}
      <div className="grid items-start gap-4 lg:grid-cols-3">
        {state.candidates.map((c) => {
          const result = results[c.id];
          return (
            <article
              className="space-y-4 rounded-2xl border bg-card p-5"
              key={c.id}
              data-testid="comparison-card"
            >
              <h2 className="break-words text-xl font-semibold">{c.name}</h2>
              {c.address && (
                <p className="break-words text-sm text-muted-foreground">
                  {c.address}
                </p>
              )}
              <p className="text-2xl font-semibold">
                {money.format(c.costs.rent)}
                <span className="ml-2 text-sm font-normal">
                  {a("fields.rent")}
                </span>
              </p>
              <p className="text-sm">
                {c.costs.utilities.basis === "unknown"
                  ? a("unknownHint")
                  : c.costs.utilities.basis === "user_bill"
                    ? a("bill")
                    : c.costs.utilities.basis === "legacy_assumption"
                      ? t("legacy")
                      : a("estimate")}
              </p>
              {c.origin && (
                <p className="text-sm text-muted-foreground">
                  {explore(`basis.${c.origin.basis}`)} ·{" "}
                  {c.origin.observed_on || a("unknown")}
                  {c.origin.source_url?.startsWith("https://") && (
                    <>
                      {" "}
                      ·{" "}
                      <a
                        className="underline"
                        href={c.origin.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {explore("source")}
                      </a>
                    </>
                  )}
                </p>
              )}
              {result ? (
                <div className="space-y-4" data-testid="comparison-result">
                  <p className="rounded-lg bg-primary/10 p-3 font-semibold">
                    {a(`fit.${result.fit}`)}
                  </p>
                  {(["summer", "winter"] as const).map((season) => (
                    <div key={season}>
                      <h3 className="font-semibold">{a(season)}</h3>
                      <dl className="mt-2 space-y-1 text-sm">
                        <div className="flex justify-between gap-3">
                          <dt>{a("total")}</dt>
                          <dd>{display(result[`${season}_total`])}</dd>
                        </div>
                        <div className="flex justify-between gap-3">
                          <dt>{a("remainder")}</dt>
                          <dd>{display(result[`${season}_remainder`])}</dd>
                        </div>
                      </dl>
                    </div>
                  ))}
                  <div className="border-t pt-3">
                    <h3 className="font-semibold">{a("moveInTitle")}</h3>
                    <p>{display(result.move_in?.cash_needed ?? null)}</p>
                    {result.move_in?.cash_needed === null && (
                      <p className="text-sm">
                        {a("subtotal", {
                          amount: money.format(result.move_in.known_subtotal),
                        })}
                      </p>
                    )}
                  </div>
                </div>
              ) : state.budget && !error ? (
                <p role="status">{a("loading")}</p>
              ) : (
                <p className="text-sm text-muted-foreground">{t("noBudget")}</p>
              )}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  disabled={!!editing}
                  onClick={() => edit(c)}
                >
                  {t("edit")}
                </Button>
                <Button
                  variant="ghost"
                  disabled={!!editing}
                  onClick={() =>
                    updateWorkspace({
                      candidates: state.candidates.filter(
                        (row) => row.id !== c.id,
                      ),
                    })
                  }
                >
                  {t("remove")}
                </Button>
              </div>
            </article>
          );
        })}
      </div>
      <p className="text-sm text-muted-foreground">{t("noRanking")}</p>
      {!editing && <ScenarioControls locale={locale} />}
    </div>
  );
}
