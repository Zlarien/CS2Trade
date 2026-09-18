export type Action = "hold" | "sell" | "trade_up";

export interface ItemRecommendation {
  item_id: string;
  action: Action;
  reason: string;
  price: number | null;
  trade_up_group: string[] | null;
}

export interface InventoryItemView {
  item_id: string;
  base_name: string;
  wear: string;
  stattrak: boolean;
  market_hash_name: string;
  excluded: boolean;
}

export interface RecommendationsResponse {
  steamid64: string;
  authenticated: boolean;
  item_count: number;
  excluded_count?: number;
  skipped_unknown_items: number;
  float_is_estimated: boolean;
  items: InventoryItemView[];
  recommendations: ItemRecommendation[];
}

export interface PortfolioSnapshot {
  captured_at: string;
  total_value: number;
  currency: string;
  item_count: number;
}

export interface InvestorAdvice {
  summary: string;
  model: string;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function steamLoginUrl(): string {
  return `${API_URL}/auth/steam/login`;
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (body?.detail) detail = body.detail;
  } catch {
    // reponse non-JSON, on garde le statusText
  }
  return new ApiError(res.status, detail);
}

export async function fetchPublicRecommendations(
  identifier: string,
): Promise<RecommendationsResponse> {
  const res = await fetch(
    `${API_URL}/inventory/recommendations?identifier=${encodeURIComponent(identifier)}`,
  );
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function fetchMyRecommendations(): Promise<RecommendationsResponse> {
  const res = await fetch(`${API_URL}/inventory/me/recommendations`, {
    credentials: "include",
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function fetchPortfolioHistory(): Promise<PortfolioSnapshot[]> {
  const res = await fetch(`${API_URL}/me/portfolio-history`, { credentials: "include" });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function excludeItem(assetId: string, reason?: string): Promise<void> {
  const res = await fetch(`${API_URL}/me/excluded-items`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ asset_id: assetId, reason }),
  });
  if (!res.ok) throw await toApiError(res);
}

export async function includeItem(assetId: string): Promise<void> {
  const res = await fetch(`${API_URL}/me/excluded-items/${encodeURIComponent(assetId)}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) throw await toApiError(res);
}

export async function fetchInvestorAdvice(question?: string): Promise<InvestorAdvice> {
  const res = await fetch(`${API_URL}/me/investor-advice`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: question || null }),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}
