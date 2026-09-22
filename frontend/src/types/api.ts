export type HealthResponse = {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
};

export type TaxCalculationRequest = {
  gross_monthly_income: number;
  pension_pillar_rate: 0.0 | 0.02 | 0.04 | 0.06;
  equalize_by: EqualizeBy;
};

export type Regime = "tooleping" | "juhatuse_liige" | "fie" | "ettevotluskonto";
export type EqualizeBy = "gross" | "payer_cost";
export type ConstraintCode =
  | "ettevotluskonto_annual_limit_exceeded"
  | "vat_registration_threshold_exceeded"
  | "fie_social_tax_minimum_applied"
  | "fie_social_tax_cap_applied";
export type ConstraintSeverity = "info" | "warning" | "blocker";

export type TaxLine = {
  name: string;
  amount: number;
};

export type Constraint = {
  code: ConstraintCode;
  severity: ConstraintSeverity;
};

export type RegimeResult = {
  regime: Regime;
  label: string;
  employer_total_cost: number;
  gross_income: number;
  breakdown: TaxLine[];
  net_income: number;
  effective_tax_rate: number;
  constraints: Constraint[];
};

export type TaxCalculationResponse = {
  input: TaxCalculationRequest;
  results: RegimeResult[];
};

export type EResidencyCalculationRequest = {
  expected_monthly_revenue: number;
  monthly_accounting_fee?: number;
};

export type EResidencyCostLine = {
  name: string;
  amount: number;
};

export type EResidencyCalculationResponse = {
  input: EResidencyCalculationRequest;
  setup_breakdown: EResidencyCostLine[];
  monthly_running_cost: number;
  first_year_total_cost: number;
  break_even_monthly_revenue: number;
  first_year_revenue: number;
  first_year_surplus: number;
};

export type DistrictRent = {
  name: string;
  avg_rent_1room: number;
  avg_rent_2room: number;
  avg_rent_3room: number;
  avg_utilities: number;
  lat: number;
  lon: number;
};

export type HousingRentsResponse = {
  city: string;
  updated_at: string;
  districts: DistrictRent[];
};

export type PlannerIncomeKind = "employment" | "manual_net";

export type PlannerEmploymentIncome = {
  kind: "employment";
  gross_monthly_income: number;
  pension_pillar_rate: 0.0 | 0.02 | 0.04 | 0.06;
};

export type PlannerManualNetIncome = {
  kind: "manual_net";
  net_monthly_income: number;
};

export type PlannerBudgetRequest = {
  income: PlannerEmploymentIncome | PlannerManualNetIncome;
  monthly_non_housing: number;
  monthly_savings: number;
  housing_share: number;
  apartment: null;
};

export type PlannerWarningCode =
  | "commitments_exceed_income"
  | "utilities_incomplete"
  | "move_in_incomplete";

export type PlannerWarning = {
  code: PlannerWarningCode;
};

export type PlannerIncome = {
  kind: PlannerIncomeKind;
  net_monthly_income: number;
  tax_year: number | null;
};

export type PlannerBudget = {
  monthly_non_housing: number;
  monthly_savings: number;
  housing_share: number;
  available_after_commitments: number;
  share_limit: number;
  housing_allowance: number;
};

export type PlannerBudgetResponse = {
  schema_version: 1;
  income: PlannerIncome;
  budget: PlannerBudget;
  apartment: null;
  warnings: PlannerWarning[];
};
