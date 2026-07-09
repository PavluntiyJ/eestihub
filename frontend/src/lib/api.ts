import type { HealthResponse } from "@/types/api";

const DEFAULT_API_URL = "http://localhost:8000";

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
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
  const url = `${baseUrl.replace(/\/$/, "")}${path}`;
  const response = await fetch(url, init);
  const body = await parseJson(response);

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status, body);
  }

  return body as TResponse;
}

export function getHealth(init?: RequestInit): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/api/v1/health", init);
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return null;
  }

  return JSON.parse(text) as unknown;
}
