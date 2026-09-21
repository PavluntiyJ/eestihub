"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";

import { THEME_STORAGE_KEY } from "@/lib/theme";

type Theme = "light" | "dark" | "system";

const THEMES: { value: Theme; Icon: typeof Sun }[] = [
  { value: "light", Icon: Sun },
  { value: "dark", Icon: Moon },
  { value: "system", Icon: Monitor },
];

function prefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(theme: Theme): void {
  const isDark = theme === "dark" || (theme === "system" && prefersDark());

  document.documentElement.classList.toggle("dark", isDark);
  document.documentElement.style.colorScheme = isDark ? "dark" : "light";
}

function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);

    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

export function ThemeToggle() {
  const t = useTranslations("theme");
  // Render the system default until the effect reads localStorage: the inline
  // script in the layout has already painted the right theme, and guessing it
  // during SSR would only produce a hydration mismatch.
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    setTheme(readStoredTheme());
  }, []);

  useEffect(() => {
    if (theme !== "system") {
      return;
    }

    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");

    query.addEventListener("change", onChange);

    return () => query.removeEventListener("change", onChange);
  }, [theme]);

  function selectTheme(next: Theme) {
    setTheme(next);
    applyTheme(next);

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // A browser with site data blocked still gets the theme for this page.
    }
  }

  return (
    <div
      aria-label={t("label")}
      className="flex items-center gap-1 rounded-full border bg-background p-1"
      role="group"
    >
      {THEMES.map(({ value, Icon }) => {
        const isActive = theme === value;

        return (
          <button
            aria-label={t(`options.${value}`)}
            aria-pressed={isActive}
            className={
              isActive
                ? "rounded-full bg-primary p-2 text-primary-foreground transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                : "rounded-full p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            }
            key={value}
            onClick={() => selectTheme(value)}
            title={t(`options.${value}`)}
            type="button"
          >
            <Icon aria-hidden="true" className="size-4" />
          </button>
        );
      })}
    </div>
  );
}
