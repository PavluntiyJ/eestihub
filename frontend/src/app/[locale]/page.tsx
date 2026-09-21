import { getTranslations, setRequestLocale } from "next-intl/server";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

type HomePageParams = {
  params: Promise<{ locale: string }>;
};

const TOOL_STEPS = [
  { href: "/calculator", key: "income" },
  { href: "/housing", key: "housing" },
  { href: "/eresidency", key: "eresidency" },
] as const;

export default async function HomePage({ params }: HomePageParams) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("home");

  return (
    <main className="flex flex-1 px-6 py-12 sm:px-8 lg:px-12" id="main-content" tabIndex={-1}>
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-14">
        <section className="grid gap-8 lg:grid-cols-[1.25fr_0.75fr] lg:items-start">
          <div className="space-y-6">
            <Badge variant="outline" className="rounded-full px-3 py-1">
              {t("hero.eyebrow")}
            </Badge>
            <div className="space-y-4">
              <h1 className="max-w-2xl font-heading text-3xl leading-[1.15] font-semibold tracking-tight text-balance sm:text-[2.5rem] sm:leading-[1.1]">
                {t("hero.title")}
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-muted-foreground">
                {t("hero.description")}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                className={cn(buttonVariants({ variant: "cta", size: "lg" }), "px-5")}
                href="/calculator"
              >
                {t("hero.primaryCta")}
              </Link>
              <Link
                className={cn(buttonVariants({ variant: "outline", size: "lg" }), "px-5")}
                href="/housing"
              >
                {t("hero.secondaryCta")}
              </Link>
            </div>
          </div>

          <Card className="bg-primary text-primary-foreground ring-0">
            <CardHeader>
              <p className="text-xs font-semibold tracking-[0.2em] uppercase opacity-80">
                {t("example.title")}
              </p>
              <p className="font-heading text-3xl font-semibold tabular-nums">
                {t("example.amount")}
              </p>
              <CardDescription className="text-primary-foreground/90">
                {t("example.description")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link
                className="text-sm font-medium underline underline-offset-4 transition-opacity hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-foreground"
                href={{
                  pathname: "/calculator",
                  query: { gross: "3000", pillar: "2", basis: "gross" },
                }}
              >
                {t("example.cta")}
              </Link>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-6">
          <div className="space-y-2">
            <h2 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
              {t("steps.title")}
            </h2>
            <p className="max-w-2xl text-muted-foreground">{t("steps.description")}</p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {TOOL_STEPS.map(({ href, key }, index) => (
              <Card className="h-full gap-2" key={key}>
                <CardHeader>
                  <span className="text-xs font-semibold tracking-[0.2em] text-primary">
                    0{index + 1}
                  </span>
                  <CardTitle>{t(`steps.items.${key}.title`)}</CardTitle>
                  <CardDescription>{t(`steps.items.${key}.text`)}</CardDescription>
                </CardHeader>
                <CardContent className="mt-auto">
                  <Link
                    className="text-sm font-medium text-primary underline underline-offset-4 hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                    href={href}
                  >
                    {t(`steps.items.${key}.cta`)}
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="max-w-3xl space-y-3">
          <h2 className="font-heading text-2xl font-semibold tracking-tight">
            {t("transparency.title")}
          </h2>
          <p className="leading-7 text-muted-foreground">{t("transparency.text")}</p>
        </section>
      </div>
    </main>
  );
}
