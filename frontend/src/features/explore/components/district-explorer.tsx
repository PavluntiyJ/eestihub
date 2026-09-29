"use client";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { calculateBudget, fetchJson } from "@/lib/api";
import type { DistrictsResponse, PlannerApartmentResult } from "@/types/api";
import {
  addCandidate,
  getWorkspace,
  updateWorkspace,
  useWorkspace,
} from "@/features/scenarios/store";
import { DistrictMap } from "./district-map";

export function DistrictExplorer({ locale }: { locale: string }) {
  const t = useTranslations("explore"),
    a = useTranslations("apartment");
  const state = useWorkspace();
  const initial = getWorkspace().explore;
  const [rooms, setRooms] = useState(initial.rooms);
  const [data, setData] = useState<DistrictsResponse | null>(null);
  const [error, setError] = useState(false),
    [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<string | null>(initial.selected);
  const [utilities, setUtilities] = useState(initial.utilities);
  const [legacy, setLegacy] = useState(initial.legacy);
  const [assessments, setAssessments] = useState<
    Record<string, PlannerApartmentResult>
  >({});
  const [assessError, setAssessError] = useState(false);
  const [notice, setNotice] = useState("");
  const valid =
    /^\d+(?:[.,]\d{1,2})?$/.test(utilities) &&
    Number(utilities.replace(",", ".")) <= 1000000;
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  });
  useEffect(() => {
    updateWorkspace({ explore: { rooms, selected, utilities, legacy } });
  }, [rooms, selected, utilities, legacy]);
  useEffect(() => {
    const abort = new AbortController();
    setData(null);
    setError(false);
    fetchJson<DistrictsResponse>(`/api/v1/planner/districts?rooms=${rooms}`, {
      signal: AbortSignal.any([abort.signal, AbortSignal.timeout(10000)]),
    })
      .then((value) => {
        if (!abort.signal.aborted) setData(value);
      })
      .catch(() => {
        if (!abort.signal.aborted) setError(true);
      });
    return () => abort.abort();
  }, [rooms, retry]);
  useEffect(() => {
    const abort = new AbortController();
    setAssessments({});
    setAssessError(false);
    if (!data || !state.budget || (!legacy && utilities !== "" && !valid))
      return () => abort.abort();
    const budget = state.budget;
    Promise.all(
      data.districts
        .filter((d) => d.rent !== null)
        .map(async (d) => {
          const amount = legacy
            ? d.legacy_utilities
            : valid
              ? Number(utilities.replace(",", "."))
              : null;
          const response = await calculateBudget(
            {
              ...budget,
              apartment: {
                rent: d.rent!,
                utilities: {
                  summer: amount,
                  winter: amount,
                  basis:
                    amount === null
                      ? "unknown"
                      : legacy
                        ? "legacy_assumption"
                        : "user_estimate",
                },
                move_in: null,
              },
            },
            {
              signal: AbortSignal.any([
                abort.signal,
                AbortSignal.timeout(10000),
              ]),
            },
          );
          return [d.id, response.apartment!] as const;
        }),
    )
      .then((rows) => {
        if (!abort.signal.aborted) setAssessments(Object.fromEntries(rows));
      })
      .catch(() => {
        if (!abort.signal.aborted) setAssessError(true);
      });
    return () => abort.abort();
  }, [data, state.budget, utilities, legacy, valid, retry]);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-5 rounded-2xl border bg-card p-5">
        <label className="space-y-2 text-sm font-medium">
          <span className="block">{t("rooms")}</span>
          <select
            className="h-12 rounded-lg border bg-background px-4"
            value={rooms}
            onChange={(e) => setRooms(Number(e.target.value))}
          >
            {[1, 2, 3].map((n) => (
              <option key={n} value={n}>
                {t("roomCount", { count: n })}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-2 text-sm font-medium">
          <span className="block">{t("utilities")}</span>
          <input
            className="h-12 w-48 rounded-lg border bg-background px-3"
            inputMode="decimal"
            value={utilities}
            disabled={legacy}
            aria-invalid={utilities !== "" && !valid && !legacy}
            aria-describedby={utilities !== "" && !valid && !legacy ? 'district-utilities-error' : undefined}
            onChange={(e) => setUtilities(e.target.value)}
          />
        </label>
        <label className="flex max-w-md items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={legacy}
            onChange={(e) => setLegacy(e.target.checked)}
          />
          {t("legacyOptIn")}
        </label>
      </div>
      {utilities !== '' && !valid && !legacy && <p id="district-utilities-error" className="text-sm text-destructive">{a('invalid')}</p>}
      <p className="text-sm text-muted-foreground">{t("context")}</p>
      {state.result ? (
        <p className="rounded-xl bg-primary/10 p-4">
          {t("allowance", {
            amount: money.format(state.result.budget.housing_allowance),
          })}{" "}
          <Link className="font-medium underline" href="/planner">
            {t("editBudget")}
          </Link>
        </p>
      ) : (
        <p className="rounded-xl border border-dashed p-4">
          {t("noBudget")}{" "}
          <Link className="font-medium underline" href="/planner">
            {t("editBudget")}
          </Link>
        </p>
      )}
      <DistrictMap
        selected={selected}
        onSelect={(id) => {
          setSelected(id);
          document
            .getElementById(`district-${id}`)
            ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }}
      />
      {error ? (
        <div role="alert">
          <p>{t("unavailable")}</p>
          <Button variant="outline" onClick={() => setRetry((n) => n + 1)}>
            {a("retry")}
          </Button>
        </div>
      ) : !data ? (
        <p role="status">{a("loading")}</p>
      ) : (
        <>
          <h2 className="text-2xl font-semibold">{t("listTitle")}</h2>
          {assessError && (
            <p role="alert">
              {t("assessmentError")}{" "}
              <button
                className="underline"
                onClick={() => setRetry((n) => n + 1)}
              >
                {a("retry")}
              </button>
            </p>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {data.districts.map((d) => {
              const result = assessments[d.id];
              return (
                <article
                  key={d.id}
                  id={`district-${d.id}`}
                  className={`space-y-3 rounded-2xl border bg-card p-5 ${selected === d.id ? "ring-2 ring-primary" : ""}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-xl font-semibold">{d.name}</h3>
                    <button
                      className="text-sm underline"
                      aria-pressed={selected === d.id}
                      onClick={() => setSelected(d.id)}
                    >
                      {t("select")}
                    </button>
                  </div>
                  <p className="text-3xl font-semibold tabular-nums">
                    {d.rent === null ? a("unknown") : money.format(d.rent)}
                    <span className="ml-2 text-sm font-normal text-muted-foreground">
                      {t("rentMonthly")}
                    </span>
                  </p>
                  <p className="text-sm">
                    {t(`basis.${d.basis}`)} · {d.observed_on || a("unknown")} ·{" "}
                    {t(`freshness.${d.freshness}`)}
                  </p>
                  {d.source_url?.startsWith("https://") && (
                    <a
                      className="block text-sm underline"
                      href={d.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {t("source")}
                    </a>
                  )}
                  {result && (
                    <div className="rounded-xl bg-muted p-3 text-sm">
                      <p className="font-semibold">{a(`fit.${result.fit}`)}</p>
                      <p>
                        {a("total")}:{" "}
                        {result.winter_total === null
                          ? a("unknown")
                          : money.format(result.winter_total)}
                      </p>
                      <p>
                        {a("remainder")}:{" "}
                        {result.winter_remainder === null
                          ? a("unknown")
                          : money.format(result.winter_remainder)}
                      </p>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    disabled={d.rent === null || state.candidates.length >= 3 || !legacy && utilities !== '' && !valid}
                    onClick={() => {
                      const amount = legacy
                        ? d.legacy_utilities
                        : valid
                          ? Number(utilities.replace(",", "."))
                          : null;
                      addCandidate({
                        id: crypto.randomUUID(),
                        name: `${d.name} · ${t("roomCount", { count: rooms })}`,
                        address: null,
                        origin: {
                          district_id: d.id,
                          rooms: rooms as 1 | 2 | 3,
                          basis: d.basis,
                          observed_on: d.observed_on,
                          source_url: d.source_url,
                        },
                        costs: {
                          rent: d.rent!,
                          utilities: {
                            summer: amount,
                            winter: amount,
                            basis:
                              amount === null
                                ? "unknown"
                                : legacy
                                  ? "legacy_assumption"
                                  : "user_estimate",
                          },
                          move_in: null,
                        },
                      });
                      setNotice("added");
                    }}
                  >
                    {t("add")}
                  </Button>
                </article>
              );
            })}
          </div>
        </>
      )}
      {notice && <p role="status">{t(notice)}</p>}
      <Link
        href="/compare"
        className="inline-flex rounded-lg bg-primary px-5 py-3 font-medium text-primary-foreground"
      >
        {t("compare", { count: state.candidates.length })}
      </Link>
    </div>
  );
}
