"use client";

import { useSyncExternalStore } from "react";
import type {
  PlannerBudgetRequest,
  PlannerBudgetResponse,
  PlannerApartmentInput,
} from "@/types/api";

export type Candidate = {
  id: string;
  name: string;
  address: string | null;
  costs: PlannerApartmentInput;
  origin?: {
    district_id: string;
    rooms: 1 | 2 | 3;
    basis: "published_aggregate" | "legacy_estimate" | "unknown";
    observed_on: string | null;
    source_url: string | null;
  };
};
export type PlannerDraft = {
  incomeKind: "employment" | "manual_net";
  grossIncome: string;
  pensionRate: "" | 0 | 0.02 | 0.04 | 0.06;
  netIncome: string;
  spending: string;
  savings: string;
  sharePercent: string;
};
export type CandidateDraft = {
  id: string;
  name: string;
  address: string;
  basis: "user_estimate" | "user_bill" | "legacy_assumption";
  values: Record<
    | "rent"
    | "summer"
    | "winter"
    | "first_rent"
    | "deposit"
    | "broker_fee"
    | "setup",
    string
  >;
};
export type Workspace = {
  budget: PlannerBudgetRequest | null;
  result: PlannerBudgetResponse | null;
  candidates: Candidate[];
  draft: PlannerDraft | null;
  candidateDraft: CandidateDraft | null;
  explore: {
    rooms: number;
    utilities: string;
    legacy: boolean;
    selected: string | null;
  };
};
const empty: Workspace = {
  budget: null,
  result: null,
  candidates: [],
  draft: null,
  candidateDraft: null,
  explore: { rooms: 1, utilities: "", legacy: false, selected: null },
};
let workspace = empty;
const listeners = new Set<() => void>();
export function updateWorkspace(patch: Partial<Workspace>) {
  workspace = { ...workspace, ...patch };
  listeners.forEach((listener) => listener());
}
export function getWorkspace() {
  return workspace;
}
export function useWorkspace() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    () => workspace,
    () => empty,
  );
}
export function addCandidate(candidate: Candidate) {
  if (workspace.candidates.length >= 3) return false;
  updateWorkspace({ candidates: [...workspace.candidates, candidate] });
  return true;
}
