"use client";

import { useTranslations } from "next-intl";

import { Link, usePathname } from "@/i18n/navigation";

const navItems = [
  { href: "/", key: "home" },
  { href: "/calculator", key: "calculator" },
  { href: "/housing", key: "housing" },
] as const;

export function SiteNav() {
  const t = useTranslations("nav");
  const pathname = usePathname();

  return (
    <nav className="flex w-full min-w-0 items-center gap-1 overflow-x-auto rounded-full border bg-background p-1 sm:w-auto">
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
                ? "shrink-0 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground"
                : "shrink-0 rounded-full px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            }
          >
            {t(item.key)}
          </Link>
        );
      })}
    </nav>
  );
}
