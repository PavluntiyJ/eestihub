import type {
  EResidencyCalculationRequest,
  EResidencyCalculationResponse,
  HealthResponse,
  HousingRentsResponse,
  TaxCalculationRequest,
  TaxCalculationResponse,
} from "@/types/api";

const DEFAULT_API_URL = "http://localhost:8000";
const DEFAULT_REQUEST_TIMEOUT_MS = 5_000;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchJson<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  // API_URL is server-only: containers reach the API over the compose network,
  // while the browser keeps the build-time NEXT_PUBLIC_API_URL.
  const baseUrl =
    process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
  const url = `${baseUrl.replace(/\/$/, "")}${path}`;
  const response = await fetch(url, {
    ...init,
    signal: init.signal ?? AbortSignal.timeout(DEFAULT_REQUEST_TIMEOUT_MS),
  });
  const body = await parseJson(response);

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status, body);
  }

  return body as TResponse;
}

export function getHealth(init?: RequestInit): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/api/v1/health", init);
}

export function getHousingRents(init?: RequestInit): Promise<HousingRentsResponse> {
  return fetchJson<HousingRentsResponse>("/api/v1/housing/rents", init);
}

export function calculateTaxes(
  request: TaxCalculationRequest,
  init: RequestInit = {}
): Promise<TaxCalculationResponse> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  return fetchJson<TaxCalculationResponse>("/api/v1/calculate-taxes", {
    ...init,
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });
}

export function calculateEResidency(
  request: EResidencyCalculationRequest,
  init: RequestInit = {}
): Promise<EResidencyCalculationResponse> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  return fetchJson<EResidencyCalculationResponse>("/api/v1/calculate-eresidency", {
    ...init,
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return null;
  }

  return JSON.parse(text) as unknown;
}
