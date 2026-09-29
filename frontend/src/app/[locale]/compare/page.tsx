import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Comparison } from "@/features/scenarios/components/comparison";
import { locales, defaultLocale, type Locale } from "@/i18n/routing";
type Props = { params: Promise<{ locale: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "compare" });
  return {
    title: t("title"),
    description: t("description"),
    robots: { index: false, follow: true },
    alternates: {
      canonical: `/${locale}/compare`,
      languages: {
        ...Object.fromEntries(locales.map((l) => [l, `/${l}/compare`])),
        "x-default": "/en/compare",
      },
    },
  };
}
export default async function Page({ params }: Props) {
  const { locale: requested } = await params;
  const locale = locales.includes(requested as Locale)
    ? requested
    : defaultLocale;
  setRequestLocale(locale);
  const t = await getTranslations("compare");
  return (
    <main id="main-content" tabIndex={-1} className="flex-1 px-5 py-10 sm:px-8">
      <div className="mx-auto max-w-[1200px] space-y-8">
        <header className="max-w-3xl space-y-3">
          <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("title")}
          </h1>
          <p className="text-lg text-muted-foreground">{t("description")}</p>
        </header>
        <Comparison locale={locale} />
      </div>
    </main>
  );
}
