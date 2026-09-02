import { ImageResponse } from "next/og";
import { getTranslations } from "next-intl/server";

import { defaultLocale, locales, type Locale } from "@/i18n/routing";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "EestiHub";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

function isLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}

export default async function OpengraphImage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale: requestedLocale } = await params;
  const locale = isLocale(requestedLocale) ? requestedLocale : defaultLocale;
  const t = await getTranslations({ locale, namespace: "metadata" });
  const nav = await getTranslations({ locale, namespace: "nav" });

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          backgroundColor: "#0f1318",
          color: "#e4e9f0",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "14px",
              height: "44px",
              backgroundColor: "#74aae9",
            }}
          />
          <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.01em" }}>
            EestiHub
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div
            style={{
              fontSize: 62,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
              maxWidth: "960px",
            }}
          >
            {t("title")}
          </div>
          <div
            style={{
              fontSize: 30,
              lineHeight: 1.35,
              color: "#9ba6b4",
              maxWidth: "900px",
            }}
          >
            {t("description")}
          </div>
        </div>

        <div style={{ display: "flex", gap: "20px", fontSize: 24, color: "#74aae9" }}>
          <div>{nav("calculator")}</div>
          <div style={{ color: "#3a4350" }}>·</div>
          <div>{nav("housing")}</div>
          <div style={{ color: "#3a4350" }}>·</div>
          <div>{nav("eresidency")}</div>
        </div>
      </div>
    ),
    size
  );
}
