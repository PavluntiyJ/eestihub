"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { getHealth } from "@/lib/api";

type BackendState = "checking" | "online" | "offline";

type BackendStatusProps = {
  apiLabel: string;
  onlineLabel: string;
  offlineLabel: string;
  checkingHelp: string;
  onlineHelp: string;
  offlineHelp: string;
};

export function BackendStatus({
  apiLabel,
  onlineLabel,
  offlineLabel,
  checkingHelp,
  onlineHelp,
  offlineHelp,
}: BackendStatusProps) {
  const [state, setState] = useState<BackendState>("checking");

  useEffect(() => {
    let active = true;

    getHealth()
      .then((health) => {
        if (active) {
          setState(health.status === "ok" && health.database === "ok" ? "online" : "offline");
        }
      })
      .catch(() => {
        if (active) {
          setState("offline");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const isOnline = state === "online";
  const statusLabel = state === "checking" ? "…" : isOnline ? onlineLabel : offlineLabel;
  const help = state === "checking" ? checkingHelp : isOnline ? onlineHelp : offlineHelp;

  return (
    <>
      <div className="flex items-center justify-between rounded-lg border bg-muted/40 p-4">
        <span className="text-sm font-medium">{apiLabel}</span>
        <Badge variant={isOnline ? "default" : "secondary"} aria-live="polite">
          {statusLabel}
        </Badge>
      </div>
      <p className="text-sm leading-6 text-muted-foreground">{help}</p>
    </>
  );
}
