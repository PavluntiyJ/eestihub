import type { PlannerApartmentInput, PlannerBudgetRequest } from "@/types/api";
import type { Candidate } from "./store";

export const STORAGE_KEY = "eestihub.planner.v1";
export type Scenario = {
  version: 1;
  currency: "EUR";
  saved_at: string;
  budget: PlannerBudgetRequest;
  candidates: Candidate[];
};
const object = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);
const keys = (x: Record<string, unknown>, allowed: string[]) =>
  Object.keys(x).every((k) => allowed.includes(k));
const money = (x: unknown): x is number =>
  typeof x === "number" &&
  Number.isFinite(x) &&
  x >= 0 &&
  x <= 1_000_000 &&
  Math.abs(x * 100 - Math.round(x * 100)) < 1e-6;
const nullable = (x: unknown) => x === null || money(x);
const label = (x: unknown, max: number): x is string =>
  typeof x === "string" &&
  x.trim().length > 0 &&
  x.length <= max &&
  !/[<>\u0000-\u001f\u007f]/.test(x);

function validCosts(x: unknown): x is PlannerApartmentInput {
  if (
    !object(x) ||
    !keys(x, ["rent", "utilities", "move_in"]) ||
    !money(x.rent) ||
    !object(x.utilities)
  )
    return false;
  const u = x.utilities;
  if (
    !keys(u, ["summer", "winter", "basis"]) ||
    !nullable(u.summer) ||
    !nullable(u.winter) ||
    typeof u.basis !== 'string' ||
    !["user_estimate", "user_bill", "legacy_assumption", "unknown"].includes(
      String(u.basis),
    )
  )
    return false;
  if ((u.basis === "unknown") !== (u.summer === null && u.winter === null))
    return false;
  return (
    x.move_in === null ||
    (object(x.move_in) &&
      keys(x.move_in, ["first_rent", "deposit", "broker_fee", "setup"]) &&
      ["first_rent", "deposit", "broker_fee", "setup"].every((k) =>
        nullable((x.move_in as Record<string, unknown>)[k]),
      ))
  );
}
export function validBudget(x: unknown): x is PlannerBudgetRequest {
  if (
    !object(x) ||
    !keys(x, [
      "income",
      "monthly_non_housing",
      "monthly_savings",
      "housing_share",
      "apartment",
    ]) ||
    x.apartment !== null ||
    !object(x.income)
  )
    return false;
  const i = x.income;
  const income =
    i.kind === "manual_net"
      ? keys(i, ["kind", "net_monthly_income"]) && money(i.net_monthly_income)
      : i.kind === "employment" &&
        keys(i, ["kind", "gross_monthly_income", "pension_pillar_rate"]) &&
        money(i.gross_monthly_income) &&
        i.gross_monthly_income > 0 &&
        [0, 0.02, 0.04, 0.06].includes(Number(i.pension_pillar_rate)) &&
        typeof i.pension_pillar_rate === "number";
  return Boolean(
    income &&
      money(x.monthly_non_housing) &&
      money(x.monthly_savings) &&
      typeof x.housing_share === "number" &&
      x.housing_share >= 0 &&
      x.housing_share <= 1 &&
      Math.abs(x.housing_share * 10000 - Math.round(x.housing_share * 10000)) <
        1e-6,
  );
}
export function parseScenario(raw: string): Scenario {
  if (new TextEncoder().encode(raw).length > 16_384) throw new Error("invalid");
  const x: unknown = JSON.parse(raw);
  if (
    !object(x) ||
    !keys(x, ["version", "currency", "saved_at", "budget", "candidates"]) ||
    x.version !== 1 ||
    x.currency !== "EUR" ||
    typeof x.saved_at !== "string" ||
    !Number.isFinite(Date.parse(x.saved_at)) ||
    !validBudget(x.budget) ||
    !Array.isArray(x.candidates) ||
    x.candidates.length > 3
  )
    throw new Error("invalid");
  const ids = new Set<string>();
  for (const c of x.candidates) {
    if (
      !object(c) ||
      !keys(c, ["id", "name", "address", "costs", "origin"]) ||
      !label(c.id, 80) ||
      ids.has(c.id) ||
      !label(c.name, 80) ||
      !(c.address === null || label(c.address, 200)) ||
      !validCosts(c.costs)
    )
      throw new Error("invalid");
    if (c.origin !== undefined) {
      const o = c.origin;
      if (
        !object(o) ||
        !keys(o, [
          "district_id",
          "rooms",
          "basis",
          "observed_on",
          "source_url",
        ]) ||
        typeof o.district_id !== 'string' || typeof o.basis !== 'string' ||
        ![
          "kesklinn",
          "pohja-tallinn",
          "kristiine",
          "mustamae",
          "lasnamae",
          "haabersti",
          "nomme",
          "pirita",
        ].includes(String(o.district_id)) ||
        ![1, 2, 3].includes(Number(o.rooms)) ||
        typeof o.rooms !== "number" ||
        !["published_aggregate", "legacy_estimate", "unknown"].includes(
          String(o.basis),
        ) ||
        !(
          o.observed_on === null ||
          (typeof o.observed_on === "string" &&
            /^\d{4}-\d{2}-\d{2}$/.test(o.observed_on))
        ) ||
        !(
          o.source_url === null ||
          (typeof o.source_url === "string" &&
            o.source_url.length <= 500 &&
            o.source_url.startsWith("https://"))
        )
      )
        throw new Error("invalid");
    }
    ids.add(c.id);
  }
  return x as Scenario;
}
export function encodeScenario(scenario: Scenario) {
  const bytes = new TextEncoder().encode(
    JSON.stringify(parseScenario(JSON.stringify(scenario))),
  );
  return btoa(Array.from(bytes, (b) => String.fromCharCode(b)).join(""))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}
export function decodeScenario(payload: string) {
  if (payload.length > 22_000 || !/^[\w-]+$/.test(payload))
    throw new Error("invalid");
  return parseScenario(
    new TextDecoder("utf-8", { fatal: true }).decode(
      Uint8Array.from(
        atob(payload.replaceAll("-", "+").replaceAll("_", "/")),
        (c) => c.charCodeAt(0),
      ),
    ),
  );
}
