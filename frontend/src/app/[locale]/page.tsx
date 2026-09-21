import { getTranslations, setRequestLocale } from "next-intl/server";

import { BackendStatus } from "@/components/backend-status";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
type HomePageParams = {
  params: Promise<{ locale: string }>;
};

export default async function HomePage({ params }: HomePageParams) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("home");

  return (
    <main
      className="flex flex-1 bg-[radial-gradient(circle_at_top_left,var(--muted),transparent_34rem)] px-6 py-12 sm:px-8 lg:px-12"
      id="main-content"
      tabIndex={-1}
    >
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
            <BackendStatus
              apiLabel={t("status.api")}
              onlineLabel={t("status.online")}
              offlineLabel={t("status.offline")}
              checkingHelp={t("status.description")}
              onlineHelp={t("status.onlineHelp")}
              offlineHelp={t("status.offlineHelp")}
            />
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
