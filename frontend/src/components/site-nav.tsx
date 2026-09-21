"use client";

import { useTranslations } from "next-intl";

import { Link, usePathname } from "@/i18n/navigation";

const navItems = [
  { href: "/", key: "home" },
  { href: "/calculator", key: "calculator" },
  { href: "/housing", key: "housing" },
  { href: "/eresidency", key: "eresidency" },
] as const;

const itemClassName =
  "shrink-0 rounded-full px-3.5 py-2 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

export function SiteNav() {
  const t = useTranslations("nav");
  const a11y = useTranslations("a11y");
  const pathname = usePathname();

  return (
    <nav
      aria-label={a11y("mainNavigation")}
      className="flex w-full min-w-0 flex-wrap items-center gap-1 rounded-2xl border border-border bg-background p-1 sm:w-auto sm:flex-nowrap sm:rounded-full"
    >
      {navItems.map((item) => {
        const isActive =
          item.href === "/" ? pathname === item.href : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={
              isActive
                ? `${itemClassName} bg-primary text-primary-foreground`
                : `${itemClassName} text-muted-foreground hover:bg-muted hover:text-foreground`
            }
          >
            {t(item.key)}
          </Link>
        );
      })}
    </nav>
  );
}
