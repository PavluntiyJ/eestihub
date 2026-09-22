"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { Map as LibreMap, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { AddressCandidate, NearbyStop } from "@/types/api";

export function TransitMap({address, stops, selected, onSelect}: {
  address: AddressCandidate; stops: NearbyStop[] | null; selected: string | null;
  onSelect: (id: string) => void;
}) {
  const t = useTranslations("transit");
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const buttons = useRef(new Map<string, HTMLButtonElement>());
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let disposed = false;
    let map: LibreMap | undefined;
    const timeout = setTimeout(() => setFailed(true), 12_000);
    import("maplibre-gl").then((lib) => {
      if (disposed || !container.current) return;
      lib.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
      map = new lib.Map({container: container.current, style: "https://tiles.openfreemap.org/styles/liberty",
        center: [address.longitude, address.latitude], zoom: 14.5, attributionControl: false,
        cooperativeGestures: true, locale: {"NavigationControl.ZoomIn": t("zoomIn"), "NavigationControl.ZoomOut": t("zoomOut"), "Map.Title": t("mapLabel")}});
      mapRef.current = map;
      map.addControl(new lib.NavigationControl({showCompass: false}), "top-right");
      map.on("load", () => { clearTimeout(timeout); if (!disposed) {setLoaded(true); setFailed(false);} });
      map.on("error", () => {if (!disposed) setFailed(true);});
      const marker = document.createElement("div");
      marker.className = "h-6 w-6 rounded-full border-4 border-white bg-primary shadow-lg";
      marker.title = address.label;
      new lib.Marker({element: marker}).setLngLat([address.longitude, address.latitude]).addTo(map);
    }).catch(() => {if (!disposed) setFailed(true);});
    return () => {disposed = true; clearTimeout(timeout); map?.remove(); mapRef.current = null;};
  }, [address.latitude, address.longitude, address.label, t]);

  useEffect(() => {
    let disposed = false;
    markers.current.forEach((m) => m.remove());
    markers.current = [];
    buttons.current.clear();
    if (!loaded || !stops) return;
    import("maplibre-gl").then((lib) => {
      if (disposed || !mapRef.current) return;
      stops.forEach((stop) => {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "flex h-8 min-w-8 items-center justify-center rounded-full border-2 border-white bg-foreground px-1 text-xs font-bold text-background shadow focus-visible:outline-4 focus-visible:outline-ring";
        element.textContent = stop.routes[0]?.short_name || "•";
        element.setAttribute("aria-label", `${stop.name}, ${t("distance", {distance: stop.straight_line_distance_m})}`);
        element.addEventListener("click", () => onSelect(stop.id));
        buttons.current.set(stop.id, element);
        element.setAttribute("aria-pressed", String(stop.id === selected));
        element.style.outline = stop.id === selected ? "3px solid var(--cta)" : "";
        markers.current.push(new lib.Marker({element}).setLngLat([stop.longitude, stop.latitude]).addTo(mapRef.current!));
      });
    });
    return () => {disposed = true; markers.current.forEach((m) => m.remove()); markers.current = [];};
  }, [stops, loaded, onSelect, t, selected]);

  useEffect(() => {
    buttons.current.forEach((button, id) => {
      button.setAttribute("aria-pressed", String(id === selected));
      button.style.outline = id === selected ? "3px solid var(--cta)" : "";
    });
    const stop = stops?.find((s) => s.id === selected);
    if (stop) mapRef.current?.easeTo({center: [stop.longitude, stop.latitude], duration: 0});
  }, [selected, stops, loaded]);

  return <div className="overflow-hidden rounded-2xl border bg-card" data-testid="transit-map">
    <div ref={container} role="region" aria-label={t("mapLabel")} className="h-72 w-full sm:h-96" />
    <div className="space-y-1 border-t p-3 text-xs text-muted-foreground">
      {failed && <p role="status" data-testid="map-unavailable">{t("mapUnavailable")}</p>}
      <p>{t("mapPrivacy")}</p>
      <p><a href="https://openfreemap.org/" className="underline" target="_blank" rel="noopener noreferrer">OpenFreeMap</a>{" · "}<a href="https://openmaptiles.org/" className="underline" target="_blank" rel="noopener noreferrer">© OpenMapTiles</a>{" · "}<a href="https://www.openstreetmap.org/copyright" className="underline" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a></p>
    </div>
  </div>;
}
