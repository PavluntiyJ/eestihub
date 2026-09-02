export type HealthResponse = {
  status: "ok";
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
