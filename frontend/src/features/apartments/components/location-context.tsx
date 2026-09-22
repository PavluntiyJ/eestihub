"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { fetchJson } from "@/lib/api";
import type { AddressCandidate, NearbyTransitResponse } from "@/types/api";
import { TransitMap } from "./transit-map";

export function LocationContext({address, locale}: {address: AddressCandidate; locale: string}) {
  const t = useTranslations("transit");
  const [response, setResponse] = useState<NearbyTransitResponse | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [showMap, setShowMap] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    setResponse(null);
    const params = new URLSearchParams({lat: String(address.latitude), lon: String(address.longitude)});
    fetchJson<NearbyTransitResponse>(`/api/v1/transit/nearby?${params}`, {
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10_000)]), cache: "no-store",
    }).then((data) => { if (!controller.signal.aborted) setResponse(data); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [address.latitude, address.longitude, retry]);
  const date = (value: string) => new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeZone: "Europe/Tallinn"}).format(new Date(value));

  return <section aria-labelledby="transit-title" className="space-y-4" data-testid="location-context">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h3 id="transit-title" className="text-xl font-semibold">{t("title")}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p></div>
      <Button type="button" variant="outline" onClick={() => setShowMap(!showMap)} aria-expanded={showMap} aria-controls="transit-map">
        {showMap ? t("hideMap") : t("showMap")}
      </Button>
    </div>
    {address.quality !== "exact" && <p className="text-sm text-warning">{t("approximate")}</p>}
    {showMap && <div id="transit-map"><TransitMap address={address} stops={response?.stops ?? null} selected={selected} onSelect={setSelected} /></div>}
    <div aria-live="polite">
      {error ? <div className="flex flex-wrap items-center gap-3 rounded-xl border p-4" data-testid="transit-unavailable">
        <p className="text-sm">{t("unavailable")}</p><Button variant="outline" type="button" onClick={() => setRetry(retry + 1)}>{t("retry")}</Button>
      </div> : !response ? <p className="text-sm">{t("loading")}</p> : <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{t("scheduled", {date: date(response.service_date)})}</p>
        {response.feed.freshness !== "current" && <p className="rounded-xl border border-warning/40 bg-warning-surface p-3 text-sm text-warning" data-testid="transit-freshness">{t(`freshness.${response.feed.freshness}`)}</p>}
        {response.stops.length === 0 ? <p className="text-sm" data-testid="transit-empty">{t("empty")}</p> : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label={t("title")}>
          {response.stops.map((stop) => <li key={stop.id}>
            <button type="button" aria-pressed={selected === stop.id} onClick={() => setSelected(stop.id)}
              className={`h-full w-full space-y-2 rounded-xl border p-4 text-left focus-visible:outline-2 focus-visible:outline-ring ${selected === stop.id ? "border-primary bg-primary/10" : "bg-card"}`}>
              <span className="flex justify-between gap-3"><span className="font-semibold">{stop.name}</span><span className="whitespace-nowrap text-sm tabular-nums">{t("distance", {distance: stop.straight_line_distance_m})}</span></span>
              <span className="block text-xs text-muted-foreground">{t("platform", {id: stop.id})}</span>
              <span className="block text-sm">{stop.routes.length ? stop.routes.map((route) => `${t(`mode.${route.mode}`)} ${route.short_name || route.long_name || route.id}`).join(" · ") : t("noRoutes")}</span>
            </button>
          </li>)}
        </ul>}
        <div className="space-y-1 break-words border-t pt-3 text-xs text-muted-foreground" data-testid="transit-attribution">
          <p>{response.feed.attribution}</p>
          <p>{t("sourceDate")}: {response.feed.source_last_modified ? date(response.feed.source_last_modified) : t("unknownDate")} · {t("checkedDate")}: {date(response.feed.checked_at)}</p>
          <p><a href={response.feed.source_url} target="_blank" rel="noopener noreferrer" className="underline">{t("source")}</a>{" · "}<a href={response.feed.license_url} target="_blank" rel="noopener noreferrer" className="underline">{response.feed.data_license}</a></p>
        </div>
      </div>}
    </div>
  </section>;
}
