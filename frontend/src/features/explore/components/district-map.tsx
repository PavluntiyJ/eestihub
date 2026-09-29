"use client";
import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { Map as LibreMap } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";
import { fetchJson } from "@/lib/api";

export function DistrictMap({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const t = useTranslations("explore");
  const transit = useTranslations("transit");
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LibreMap | null>(null);
  const callback = useRef(onSelect);
  callback.current = onSelect;
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let disposed = false;
    let map: LibreMap | undefined;
    const abort = new AbortController();
    const timer = setTimeout(() => {
      if (!disposed) setFailed(true);
    }, 12000);
    Promise.all([
      import("maplibre-gl"),
      fetchJson<FeatureCollection>("/api/v1/planner/district-boundaries", {
        signal: AbortSignal.any([abort.signal, AbortSignal.timeout(10000)]),
      }),
    ])
      .then(([lib, data]) => {
        if (disposed || !container.current) return;
        lib.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        map = new lib.Map({
          container: container.current,
          style: "https://tiles.openfreemap.org/styles/liberty",
          center: [24.75, 59.435],
          zoom: 10,
          attributionControl: false,
          cooperativeGestures: true,
          locale: {
            "Map.Title": t("mapTitle"),
            "NavigationControl.ZoomIn": transit("zoomIn"),
            "NavigationControl.ZoomOut": transit("zoomOut"),
          },
        });
        mapRef.current = map;
        map.addControl(new lib.NavigationControl({ showCompass: false }));
        map.on("load", () => {
          if (disposed || !map) return;
          map.addSource("districts", { type: "geojson", data });
          map.addLayer({
            id: "district-fill",
            type: "fill",
            source: "districts",
            paint: { "fill-color": "#147d70", "fill-opacity": 0.18 },
          });
          map.addLayer({
            id: "district-line",
            type: "line",
            source: "districts",
            paint: { "line-color": "#12665d", "line-width": 2 },
          });
          map.on("click", "district-fill", (event) => {
            const id = event.features?.[0]?.properties?.id;
            if (typeof id === "string") callback.current(id);
          });
          map.on("mouseenter", "district-fill", () => {
            if (map) map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", "district-fill", () => {
            if (map) map.getCanvas().style.cursor = "";
          });
          clearTimeout(timer);
          setLoaded(true);
          setFailed(false);
        });
        map.on("error", () => {
          if (!disposed) setFailed(true);
        });
      })
      .catch(() => {
        if (!disposed) setFailed(true);
      });
    return () => {
      disposed = true;
      abort.abort();
      clearTimeout(timer);
      map?.remove();
      mapRef.current = null;
    };
  }, [t, transit]);
  useEffect(() => {
    if (loaded && mapRef.current?.getLayer("district-fill"))
      mapRef.current.setPaintProperty("district-fill", "fill-opacity", [
        "case",
        ["==", ["get", "id"], selected || ""],
        0.55,
        0.18,
      ]);
  }, [loaded, selected]);
  return (
    <div className="overflow-hidden rounded-2xl border bg-card">
      <div
        ref={container}
        className="h-80 w-full sm:h-[440px]"
        data-testid="district-map"
      />
      <div className="space-y-1 p-3 text-xs text-muted-foreground">
        {failed && <p role="status">{t("mapUnavailable")}</p>}
        <p>{t("mapHint")}</p>
        <p>
          <a
            className="underline"
            href="https://geoportaal.maaruum.ee/est/ruumiandmed/haldus-ja-asustusjaotus-p119.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            Maa- ja Ruumiamet · EHAK 2026-09-02
          </a>
        </p>
        <p>
          <a className="underline" href="https://openfreemap.org/">
            OpenFreeMap
          </a>{" "}
          ·{" "}
          <a className="underline" href="https://openmaptiles.org/">
            © OpenMapTiles
          </a>{" "}
          ·{" "}
          <a
            className="underline"
            href="https://www.openstreetmap.org/copyright"
          >
            © OpenStreetMap contributors
          </a>
        </p>
      </div>
    </div>
  );
}
