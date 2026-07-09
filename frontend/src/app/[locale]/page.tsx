import { getTranslations } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getHealth } from "@/lib/api";

export const dynamic = "force-dynamic";

type BackendStatus = {
  online: boolean;
};

async function getBackendStatus(): Promise<BackendStatus> {
  try {
    const health = await getHealth({ cache: "no-store" });

    return { online: health.status === "ok" };
  } catch {
    return { online: false };
  }
}

export default async function HomePage() {
  const t = await getTranslations("home");
  const backendStatus = await getBackendStatus();

  return (
    <main className="flex flex-1 bg-[radial-gradient(circle_at_top_left,var(--muted),transparent_34rem)] px-6 py-12 sm:px-8 lg:px-12">
      <div className="mx-auto grid w-full max-w-6xl gap-8 lg:grid-cols-[1.3fr_0.7fr] lg:items-center">
        <section className="space-y-8">
          <div className="space-y-5">
            <Badge variant="outline" className="rounded-full px-3 py-1">
              {t("hero.eyebrow")}
            </Badge>
            <div className="space-y-4">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
                {t("hero.title")}
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">
                {t("hero.description")}
              </p>
            </div>
          </div>
          <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-3">
            <div className="rounded-xl border bg-background/70 p-4">{t("proof.tax")}</div>
            <div className="rounded-xl border bg-background/70 p-4">{t("proof.housing")}</div>
            <div className="rounded-xl border bg-background/70 p-4">{t("proof.i18n")}</div>
          </div>
        </section>

        <Card className="border-border/70 bg-background/90 shadow-sm">
          <CardHeader>
            <CardTitle>{t("status.title")}</CardTitle>
            <CardDescription>{t("status.description")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between rounded-lg border bg-muted/40 p-4">
              <span className="text-sm font-medium">{t("status.api")}</span>
              <Badge variant={backendStatus.online ? "default" : "secondary"}>
                {backendStatus.online ? t("status.online") : t("status.offline")}
              </Badge>
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              {backendStatus.online ? t("status.onlineHelp") : t("status.offlineHelp")}
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
