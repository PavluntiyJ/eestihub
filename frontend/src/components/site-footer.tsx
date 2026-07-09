import { getTranslations } from "next-intl/server";

export async function SiteFooter() {
  const t = await getTranslations("footer");
  const year = new Date().getFullYear();

  return (
    <footer className="border-t bg-muted/50 px-6 py-6 sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
        <span>© {year} EestiHub</span>
        <span>{t("line")}</span>
        <span className="flex items-center gap-4">
          <a
            href="https://github.com/PavluntiyJ/eestihub"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            {t("github")}
          </a>
          <a
            href="https://www.emta.ee"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            {t("emta")}
          </a>
        </span>
      </div>
    </footer>
  );
}
