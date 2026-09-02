"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DistrictRent, RegimeResult } from "@/types/api";

// The 30% rule of thumb is a starting point, not a law: the control lets the
// user argue with it, which is the point of showing the number at all.
const DEFAULT_HOUSING_SHARE = 0.3;
const HOUSING_SHARE_MIN = 0.15;
const HOUSING_SHARE_MAX = 0.5;
const HOUSING_SHARE_STEP = 0.05;

type RoomKey = "oneRoom" | "twoRoom" | "threeRoom";

const ROOM_OPTIONS: { key: RoomKey; rentField: keyof DistrictRent }[] = [
  { key: "threeRoom", rentField: "avg_rent_3room" },
  { key: "twoRoom", rentField: "avg_rent_2room" },
  { key: "oneRoom", rentField: "avg_rent_1room" },
];

type AffordableDistrict = {
  name: string;
  room: RoomKey;
  rent: number;
  utilities: number;
  total: number;
};

function findLargestAffordable(
  district: DistrictRent,
  budget: number
): AffordableDistrict | null {
  for (const option of ROOM_OPTIONS) {
    const rent = district[option.rentField] as number;
    const total = rent + district.avg_utilities;

    if (total <= budget) {
      return {
        name: district.name,
        room: option.key,
        rent,
        utilities: district.avg_utilities,
        total,
      };
    }
  }

  return null;
}

export function AffordabilityPanel({
  districts,
  locale,
  topResult,
}: {
  districts: DistrictRent[];
  locale: string;
  topResult: RegimeResult;
}) {
  const t = useTranslations("affordability");
  const tCalculator = useTranslations("calculator");
  const tHousing = useTranslations("housing");
  const shareInputId = useId();
  const [share, setShare] = useState(DEFAULT_HOUSING_SHARE);

  const moneyFormatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  });
  const percentFormatter = new Intl.NumberFormat(locale, {
    style: "percent",
    maximumFractionDigits: 0,
  });

  const budget = Math.floor(Math.max(topResult.net_income, 0) * share);
  const affordable = districts
    .map((district) => findLargestAffordable(district, budget))
    .filter((entry): entry is AffordableDistrict => entry !== null)
    .sort((left, right) => right.total - left.total);

  return (
    <Card className="bg-background/95 shadow-sm">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>
          {t("description")}{" "}
          {t("basedOn", { regime: tCalculator(`regime.${topResult.regime}`) })}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor={shareInputId}>
              {t("shareLabel", { share: percentFormatter.format(share) })}
            </label>
            <input
              className="w-full accent-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              id={shareInputId}
              max={HOUSING_SHARE_MAX}
              min={HOUSING_SHARE_MIN}
              onChange={(event) => setShare(Number(event.target.value))}
              step={HOUSING_SHARE_STEP}
              type="range"
              value={share}
            />
          </div>
          <div className="rounded-xl border bg-muted/30 p-3">
            <div className="text-xs text-muted-foreground">{t("budget")}</div>
            <div className="mt-1 font-mono text-sm font-semibold tabular-nums">
              {moneyFormatter.format(budget)}
            </div>
          </div>
        </div>

        {affordable.length > 0 ? (
          <ul className="divide-y rounded-lg border">
            {affordable.map((entry) => (
              <li
                className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-3 py-2 text-sm"
                data-affordable-district={entry.name}
                key={entry.name}
              >
                <span className="font-medium">{entry.name}</span>
                <span className="text-muted-foreground">
                  {tHousing(`table.columns.${entry.room}`)}
                </span>
                <span className="font-mono tabular-nums">
                  {moneyFormatter.format(entry.total)}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {t("rentAndUtilities", {
                      rent: moneyFormatter.format(entry.rent),
                      utilities: moneyFormatter.format(entry.utilities),
                    })}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-lg border border-dashed px-3 py-4 text-sm text-muted-foreground">
            {t("none")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
