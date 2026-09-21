import { getTranslations } from "next-intl/server";

const linkClassName =
  "underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

export async function SiteFooter() {
  const t = await getTranslations("footer");
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-card px-6 py-6 sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
        <span>© {year} EestiHub</span>
        <span>{t("line")}</span>
        <span className="flex items-center gap-4">
          <a
            className={linkClassName}
            href="https://github.com/PavluntiyJ/eestihub"
            rel="noopener noreferrer"
            target="_blank"
          >
            {t("github")}
          </a>
          <a
            className={linkClassName}
            href="https://www.emta.ee"
            rel="noopener noreferrer"
            target="_blank"
          >
            {t("emta")}
          </a>
        </span>
      </div>
    </footer>
  );
}
