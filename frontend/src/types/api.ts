export type HealthResponse = {
  status: "ok";
};

export type TaxCalculationRequest = {
  gross_monthly_income: number;
  pension_pillar_rate: 0.0 | 0.02 | 0.04 | 0.06;
};

export type Regime = "tooleping" | "juhatuse_liige" | "fie" | "ettevotluskonto";

export type TaxLine = {
  name: string;
  amount: number;
};

export type RegimeResult = {
  regime: Regime;
  label: string;
  employer_total_cost: number;
  gross_income: number;
  breakdown: TaxLine[];
  net_income: number;
  effective_tax_rate: number;
};

export type TaxCalculationResponse = {
  input: TaxCalculationRequest;
  results: RegimeResult[];
};
