import type { EqualizeBy, TaxCalculationRequest } from "@/types/api";

export type PensionPillarRate = TaxCalculationRequest["pension_pillar_rate"];

export type Scenario = {
  grossMonthlyIncome: string;
  pensionPillarRate: PensionPillarRate;
  equalizeBy: EqualizeBy;
};

export const DEFAULT_SCENARIO: Scenario = {
  grossMonthlyIncome: "3000",
  pensionPillarRate: 0.02,
  equalizeBy: "gross",
};

// The URL contract, deliberately readable: whole percent for the pillar rather
// than 0.02, and the API's own values for the basis. A later task will generate
// links against exactly these names, so changing them is a breaking change.
export const SCENARIO_PARAMS = {
  gross: "gross",
  pillar: "pillar",
  basis: "basis",
} as const;

const PILLAR_BY_PERCENT = new Map<string, PensionPillarRate>([
  ["0", 0],
  ["2", 0.02],
  ["4", 0.04],
  ["6", 0.06],
]);

export function pillarToPercent(rate: PensionPillarRate): string {
  return String(Math.round(rate * 100));
}

export function parseGrossIncome(raw: string): number {
  return Number(raw.trim().replace(",", "."));
}

export function isGrossIncomeValid(raw: string): boolean {
  const value = parseGrossIncome(raw);

  return Number.isFinite(value) && value > 0;
}

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/**
 * Reads a scenario out of query parameters. Anything missing or malformed
 * falls back to the default, so a hand-typed junk URL renders the normal form
 * rather than an error.
 */
export function scenarioFromParams(
  params:
    | URLSearchParams
    | Record<string, string | string[] | undefined>
): { scenario: Scenario; hasExplicitIncome: boolean } {
  const read = (key: string): string | undefined =>
    params instanceof URLSearchParams
      ? params.get(key) ?? undefined
      : firstValue(params[key]);

  const rawGross = read(SCENARIO_PARAMS.gross);
  const hasExplicitIncome = rawGross !== undefined && isGrossIncomeValid(rawGross);
  const rawPillar = read(SCENARIO_PARAMS.pillar);
  const rawBasis = read(SCENARIO_PARAMS.basis);

  return {
    scenario: {
      grossMonthlyIncome: hasExplicitIncome
        ? (rawGross as string).trim()
        : DEFAULT_SCENARIO.grossMonthlyIncome,
      pensionPillarRate:
        (rawPillar !== undefined ? PILLAR_BY_PERCENT.get(rawPillar) : undefined) ??
        DEFAULT_SCENARIO.pensionPillarRate,
      equalizeBy:
        rawBasis === "payer_cost" || rawBasis === "gross"
          ? rawBasis
          : DEFAULT_SCENARIO.equalizeBy,
    },
    hasExplicitIncome,
  };
}

export function scenarioToQuery(scenario: Scenario): string {
  const query = new URLSearchParams({
    [SCENARIO_PARAMS.gross]: String(parseGrossIncome(scenario.grossMonthlyIncome)),
    [SCENARIO_PARAMS.pillar]: pillarToPercent(scenario.pensionPillarRate),
    [SCENARIO_PARAMS.basis]: scenario.equalizeBy,
  });

  return query.toString();
}
