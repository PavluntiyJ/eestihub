"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, searchAddresses } from "@/lib/api";
import type {
  AddressAttribution,
  AddressCandidate,
  AddressProviderErrorCode,
} from "@/types/api";

const SEARCH_DEBOUNCE_MS = 500;
const AUTO_SEARCH_MIN_LENGTH = 4;
const EXPLICIT_SEARCH_MIN_LENGTH = 3;

type SearchStatus =
  | "idle"
  | "loading"
  | "results"
  | "empty"
  | "unavailable"
  | "busy";

function providerErrorCode(body: unknown): AddressProviderErrorCode | null {
  if (
    typeof body === "object" &&
    body !== null &&
    "detail" in body &&
    typeof (body as { detail: unknown }).detail === "object" &&
    (body as { detail: unknown }).detail !== null &&
    "code" in (body as { detail: { code: unknown } }).detail
  ) {
    const code = (body as { detail: { code: unknown } }).detail.code;
    if (code === "address_search_busy" || code === "address_provider_unavailable") {
      return code;
    }
  }

  return null;
}

// Optional Tallinn address lookup mounted below a calculated budget. It only
// selects location context: results never touch budget arithmetic, nothing
// is persisted, and the query never leaves the client except to the API.
export function AddressSearch() {
  const t = useTranslations("addresses");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [candidates, setCandidates] = useState<AddressCandidate[]>([]);
  // The announced hit count is stored separately: selecting an address
  // clears the dropdown candidates while the search result stands.
  const [resultCount, setResultCount] = useState(0);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [hint, setHint] = useState<string | null>(null);
  const [selected, setSelected] = useState<AddressCandidate | null>(null);
  const [attribution, setAttribution] = useState<AddressAttribution | null>(null);
  const requestIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const runSearch = useCallback(async (text: string) => {
    const trimmed = text.trim();

    if (trimmed.length < EXPLICIT_SEARCH_MIN_LENGTH) {
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = (requestIdRef.current += 1);

    setStatus("loading");
    setHint(null);
    setOpen(true);

    try {
      const response = await searchAddresses(trimmed, { signal: controller.signal });

      if (requestIdRef.current !== requestId) {
        return;
      }

      setCandidates(response.candidates);
      setResultCount(response.candidates.length);
      setAttribution(response.attribution);
      setActiveIndex(-1);
      setStatus(response.candidates.length === 0 ? "empty" : "results");
    } catch (caughtError) {
      if (requestIdRef.current !== requestId) {
        return;
      }

      if (caughtError instanceof Error && caughtError.name === "AbortError") {
        return;
      }

      // The typed query is preserved; only the dropdown state resets.
      setCandidates([]);
      setActiveIndex(-1);
      const code =
        caughtError instanceof ApiError ? providerErrorCode(caughtError.body) : null;
      setStatus(code === "address_search_busy" ? "busy" : "unavailable");
    }
  }, []);

  // Automatic search only from four characters; explicit search accepts three.
  useEffect(() => {
    if (query.trim().length < AUTO_SEARCH_MIN_LENGTH) {
      return;
    }

    const timer = window.setTimeout(() => void runSearch(query), SEARCH_DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [query, runSearch]);

  useEffect(() => {
    const pending = abortRef;

    return () => {
      pending.current?.abort();
    };
  }, []);

  function clearAll() {
    abortRef.current?.abort();
    abortRef.current = null;
    requestIdRef.current += 1;
    setQuery("");
    setSelected(null);
    setCandidates([]);
    setActiveIndex(-1);
    setStatus("idle");
    setHint(null);
    setOpen(false);
  }

  function selectCandidate(candidate: AddressCandidate) {
    setSelected(candidate);
    setQuery(candidate.short_label);
    setCandidates([]);
    setActiveIndex(-1);
    setOpen(false);
  }

  function onQueryChange(value: string) {
    // Any edit immediately drops the previous selection: it no longer
    // describes what the field contains.
    setSelected(null);
    setQuery(value);
    setHint(null);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (candidates.length === 0) {
        return;
      }

      event.preventDefault();
      setOpen(true);
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => {
        if (current === -1) {
          return step === 1 ? 0 : candidates.length - 1;
        }

        return (current + step + candidates.length) % candidates.length;
      });
    } else if (event.key === "Enter") {
      if (open && activeIndex >= 0 && activeIndex < candidates.length) {
        event.preventDefault();
        selectCandidate(candidates[activeIndex]);
      } else if (query.trim().length >= EXPLICIT_SEARCH_MIN_LENGTH) {
        event.preventDefault();
        void runSearch(query);
      } else {
        event.preventDefault();
        setHint(t("minLength"));
      }
    } else if (event.key === "Escape") {
      if (open) {
        setOpen(false);
        setActiveIndex(-1);
      } else {
        clearAll();
      }
    }
  }

  const statusMessage =
    status === "loading"
      ? t("loading")
      : status === "results"
        ? t("resultsAnnounced", { count: resultCount })
        : status === "empty"
          ? t("empty")
          : status === "unavailable"
            ? t("unavailable")
            : status === "busy"
              ? t("busy")
              : null;

  return (
    <section aria-labelledby="address-search-title" data-testid="address-search">
      <Card className="bg-background/95 shadow-sm">
        <CardHeader>
          <CardTitle id="address-search-title">{t("title")}</CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <label className="sr-only" htmlFor="address-search-input">
                {t("searchLabel")}
              </label>
              <input
                aria-activedescendant={
                  activeIndex >= 0 ? `address-option-${activeIndex}` : undefined
                }
                aria-controls="address-search-listbox"
                aria-expanded={open && candidates.length > 0}
                autoComplete="off"
                className="h-12 w-full rounded-lg border bg-background px-3 text-sm outline-none transition focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                id="address-search-input"
                inputMode="search"
                onChange={(event) => onQueryChange(event.target.value)}
                onKeyDown={onKeyDown}
                placeholder={t("searchPlaceholder")}
                ref={inputRef}
                role="combobox"
                type="text"
                value={query}
              />
              {open && candidates.length > 0 ? (
                <ul
                  className="absolute inset-x-0 top-full z-10 mt-1 max-h-64 overflow-auto rounded-lg border bg-background shadow-lg"
                  id="address-search-listbox"
                  role="listbox"
                >
                  {candidates.map((candidate, index) => (
                    <li
                      aria-selected={index === activeIndex}
                      className={`cursor-pointer px-3 py-2 text-sm ${
                        index === activeIndex ? "bg-primary/10" : ""
                      }`}
                      id={`address-option-${index}`}
                      key={candidate.id}
                      onMouseDown={(event) => {
                        // Select before the input loses focus and closes.
                        event.preventDefault();
                        selectCandidate(candidate);
                      }}
                      role="option"
                    >
                      <span className="block font-medium">{candidate.short_label}</span>
                      <span className="block text-xs text-muted-foreground">
                        {candidate.label}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <Button
              onClick={() => {
                if (query.trim().length >= EXPLICIT_SEARCH_MIN_LENGTH) {
                  void runSearch(query);
                } else {
                  setHint(t("minLength"));
                  inputRef.current?.focus();
                }
              }}
              type="button"
              variant="outline"
            >
              {t("searchButton")}
            </Button>
          </div>

          <div aria-live="polite" className="min-h-5 text-sm" role="status">
            {hint ?? statusMessage}
          </div>

          {status === "unavailable" || status === "busy" ? (
            <Button onClick={() => void runSearch(query)} size="sm" type="button" variant="outline">
              {t("retry")}
            </Button>
          ) : null}

          {selected ? (
            <div
              className="space-y-2 rounded-xl border border-primary/30 bg-primary/5 p-3"
              data-testid="address-selected"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{selected.label}</p>
                  <p className="mt-1 font-mono text-xs tabular-nums text-muted-foreground">
                    {t("coordinates")}: {selected.longitude}, {selected.latitude} ·{" "}
                    {t(`quality.${selected.quality}`)}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{t("contextNote")}</p>
                </div>
                <Button
                  data-testid="address-clear"
                  onClick={clearAll}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  {t("clear")}
                </Button>
              </div>
            </div>
          ) : null}

          {attribution ? (
            <p className="text-xs text-muted-foreground" data-testid="address-attribution">
              {attribution.label} ·{" "}
              <a
                className="underline underline-offset-4 hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                href={attribution.source_url}
                rel="noopener noreferrer"
                target="_blank"
              >
                {t("attributionLink")}
              </a>
            </p>
          ) : null}
        </CardContent>
      </Card>
    </section>
  );
}
