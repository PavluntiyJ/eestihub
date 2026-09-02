import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import "../globals.css";

import { SiteHeader } from "@/components/site-header";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import { SiteFooter } from "@/components/site-footer";
import { defaultLocale, locales, type Locale } from "@/i18n/routing";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

type LocaleParams = {
  params: Promise<{ locale: string }>;
};

const themeScript = `(function(){try{var s=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY
)});var d=s==="dark"||(s!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);var e=document.documentElement;e.classList.toggle("dark",d);e.style.colorScheme=d?"dark":"light";}catch(e){}})();`;

function isLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: LocaleParams): Promise<Metadata> {
  const { locale: requestedLocale } = await params;
  const locale = isLocale(requestedLocale) ? requestedLocale : defaultLocale;
  const t = await getTranslations({ locale, namespace: "metadata" });

  return {
    metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
    title: t("title"),
    description: t("description"),
    openGraph: {
      title: t("title"),
      description: t("description"),
      type: "website",
    },
    alternates: {
      canonical: `/${locale}`,
      languages: {
        ...Object.fromEntries(
          locales.map((alternateLocale) => [alternateLocale, `/${alternateLocale}`])
        ),
        "x-default": "/en",
      },
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <html
      lang={locale}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full bg-background text-foreground">
        {/* Applies the stored theme before the body paints, so the page never
            flashes the wrong one. Must stay inline and synchronous; Next
            strips scripts from a hand-written <head>. */}
        <script
          dangerouslySetInnerHTML={{ __html: themeScript }}
          suppressHydrationWarning
        />
        <NextIntlClientProvider>
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            {children}
            <SiteFooter />
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
