"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LocaleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors");

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main
      className="flex flex-1 items-center px-6 py-16 sm:px-8 lg:px-12"
      id="main-content"
      tabIndex={-1}
    >
      <Card className="mx-auto w-full max-w-xl border-destructive/40 bg-background/95 shadow-sm">
        <CardHeader className="space-y-4">
          <div className="space-y-2">
            <CardTitle>{t("boundary.title")}</CardTitle>
            <CardDescription>{t("boundary.description")}</CardDescription>
          </div>
          <div>
            <Button onClick={reset} type="button">
              {t("boundary.retry")}
            </Button>
          </div>
        </CardHeader>
      </Card>
    </main>
  );
}
