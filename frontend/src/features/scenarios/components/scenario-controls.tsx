"use client";
import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { calculateBudget } from "@/lib/api";
import { useWorkspace, updateWorkspace } from "../store";
import {
  decodeScenario,
  encodeScenario,
  parseScenario,
  STORAGE_KEY,
  type Scenario,
} from "../serializer";

export function ScenarioControls({ locale }: { locale: string }) {
  const t = useTranslations("scenarios");
  const state = useWorkspace();
  const [pending, setPending] = useState<Scenario | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [addresses, setAddresses] = useState(false);
  const [gross, setGross] = useState(false);
  const [preview, setPreview] = useState(false);
  const [link, setLink] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    function readHash() {
      if (!window.location.hash.startsWith("#plan=")) return;
      try {
        if (window.location.href.length > 6000) throw new Error();
        setPending(decodeScenario(window.location.hash.slice(6)));
      } catch {
        setStatus("invalid");
      }
    }
    readHash();
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
  }, []);
  useEffect(() => {
    setLink("");
    setPreview(false);
  }, [state.budget, state.candidates, addresses, gross]);
  function current(sharing = false): Scenario {
    if (!state.budget || !state.result) throw new Error("budget");
    return parseScenario(
      JSON.stringify({
        version: 1,
        currency: "EUR",
        saved_at: new Date().toISOString(),
        budget: {
          ...state.budget,
          apartment: null,
          income:
            sharing && !gross
              ? {
                  kind: "manual_net",
                  net_monthly_income: state.result.income.net_monthly_income,
                }
              : state.budget.income,
        },
        candidates: state.candidates.map((c, i) =>
          sharing && !addresses
            ? {
                ...c,
                name: `Apartment ${String.fromCharCode(65 + i)}`,
                id: `shared-${i + 1}`,
                address: null,
                origin: undefined,
              }
            : c,
        ),
      }),
    );
  }
  async function accept() {
    if (!pending) return;
    setBusy(true);
    setStatus("");
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    try {
      const result = await calculateBudget(pending.budget, {
        signal: AbortSignal.any([abort.signal, AbortSignal.timeout(10000)]),
      });
      if (abort.signal.aborted) return;
      updateWorkspace({
        budget: pending.budget,
        result,
        candidates: pending.candidates,
        draft: null,
        candidateDraft: null,
      });
      setPending(null);
      setStatus("imported");
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
      window.dispatchEvent(new Event("hashchange"));
    } catch {
      if (!abort.signal.aborted) setStatus("failed");
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }
  return (
    <section
      className="space-y-4 rounded-2xl border bg-card p-5"
      aria-label={t("title")}
    >
      <h2 className="text-xl font-semibold">{t("title")}</h2>
      <p className="text-sm text-muted-foreground">{t("privacy")}</p>
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={!state.budget || !state.result}
          onClick={() => {
            try {
              localStorage.setItem(STORAGE_KEY, JSON.stringify(current()));
              setStatus("saved");
            } catch {
              setStatus("failed");
            }
          }}
        >
          {t("save")}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            try {
              const raw = localStorage.getItem(STORAGE_KEY);
              if (!raw) {
                setStatus("noSaved");
                return;
              }
              setPending(parseScenario(raw));
              setStatus("");
            } catch {
              setStatus("invalid");
            }
          }}
        >
          {t("load")}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            try {
              localStorage.removeItem(STORAGE_KEY);
              setStatus("deleted");
            } catch {
              setStatus("failed");
            }
          }}
        >
          {t("delete")}
        </Button>
        <Button
          variant="outline"
          disabled={!state.budget || !state.result}
          onClick={() => {
            try {
              const blob = new Blob([JSON.stringify(current(), null, 2)], {
                type: "application/json",
              });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "eestihub-plan.json";
              a.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            } catch {
              setStatus("failed");
            }
          }}
        >
          {t("export")}
        </Button>
        <label className="inline-flex cursor-pointer items-center rounded-lg border px-3 py-2 text-sm">
          {t("import")}
          <input
            className="sr-only"
            type="file"
            accept="application/json,.json"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (!file) return;
              try {
                if (file.size > 16384) throw new Error();
                setPending(parseScenario(await file.text()));
                setStatus("");
              } catch {
                setStatus("invalid");
              }
            }}
          />
        </label>
      </div>
      {pending && (
        <div
          className="space-y-3 rounded-xl border border-primary p-4"
          data-testid="scenario-review"
        >
          <h3 className="font-semibold">{t("review")}</h3>
          <p>
            {t("reviewHint", {
              count: pending.candidates.length,
              date: new Date(pending.saved_at).toLocaleDateString(locale),
            })}
          </p>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all text-xs">
            {JSON.stringify(pending, null, 2)}
          </pre>
          <Button disabled={busy} onClick={accept}>
            {busy ? t("loading") : t("apply")}
          </Button>{" "}
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => setPending(null)}
          >
            {t("cancel")}
          </Button>
        </div>
      )}
      <details className="space-y-3 border-t pt-3">
        <summary className="cursor-pointer font-semibold">{t("share")}</summary>
        <p className="text-sm text-muted-foreground">{t("shareHint")}</p>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={addresses}
            onChange={(e) => setAddresses(e.target.checked)}
          />
          {t("includeAddress")}
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={gross}
            onChange={(e) => setGross(e.target.checked)}
          />
          {t("includeGross")}
        </label>
        <Button
          disabled={!state.budget || !state.result}
          variant="outline"
          onClick={() => setPreview(true)}
        >
          {t("preview")}
        </Button>
        {preview && state.budget && state.result && (
          <div className="space-y-3">
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all text-xs">
              {JSON.stringify(current(true), null, 2)}
            </pre>
            <Button
              onClick={() => {
                try {
                  const url = `${window.location.origin}/${locale}/compare#plan=${encodeScenario(current(true))}`;
                  if (url.length > 6000) {
                    setStatus("tooLong");
                    return;
                  }
                  setLink(url);
                  setStatus("");
                } catch {
                  setStatus("failed");
                }
              }}
            >
              {t("generate")}
            </Button>
          </div>
        )}
        {link && (
          <label className="block text-sm">
            {t("link")}
            <textarea
              readOnly
              value={link}
              className="mt-2 h-24 w-full rounded-lg border bg-background p-3"
              onFocus={(e) => e.target.select()}
            />
          </label>
        )}
      </details>
      {status && (
        <p role="status" className="text-sm">
          {t(status)}
        </p>
      )}
    </section>
  );
}
