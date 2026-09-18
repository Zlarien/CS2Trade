"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  excludeItem,
  fetchMyRecommendations,
  fetchPortfolioHistory,
  fetchPublicRecommendations,
  includeItem,
  type ItemRecommendation,
  type PortfolioSnapshot,
  type RecommendationsResponse,
} from "../../lib/api";

export const dynamic = "force-dynamic";

const ACTION_LABELS: Record<ItemRecommendation["action"], string> = {
  hold: "Garder",
  sell: "Vendre",
  trade_up: "Trade-up",
};

export default function InventoryPage() {
  return (
    <Suspense fallback={<main><p>Chargement...</p></main>}>
      <InventoryView />
    </Suspense>
  );
}

function InventoryView() {
  const searchParams = useSearchParams();
  const identifier = searchParams.get("identifier");

  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [history, setHistory] = useState<PortfolioSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingItemId, setPendingItemId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = identifier
        ? await fetchPublicRecommendations(identifier)
        : await fetchMyRecommendations();
      setData(result);
      if (result.authenticated) {
        try {
          setHistory(await fetchPortfolioHistory());
        } catch {
          setHistory([]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, [identifier]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleExclusion(itemId: string, currentlyExcluded: boolean) {
    setPendingItemId(itemId);
    try {
      if (currentlyExcluded) {
        await includeItem(itemId);
      } else {
        await excludeItem(itemId);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "erreur inconnue");
    } finally {
      setPendingItemId(null);
    }
  }

  if (loading) {
    return (
      <main>
        <p>Chargement...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main>
        <p>Erreur : {error}</p>
        <Link href="/">Retour</Link>
      </main>
    );
  }

  if (!data) return null;

  const recommendationsByItemId = new Map(data.recommendations.map((r) => [r.item_id, r]));

  return (
    <main>
      <h1>Inventaire {data.steamid64}</h1>
      <p>
        {data.item_count} item(s) reconnu(s)
        {data.skipped_unknown_items > 0 &&
          `, ${data.skipped_unknown_items} ignore(s) (hors referentiel)`}
        .{" "}
        {data.float_is_estimated &&
          "Float approxime (Steam ne l'expose pas via ses APIs publiques)."}
      </p>

      {history.length > 1 && <PortfolioChart snapshots={history} />}

      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Action</th>
            <th>Raison</th>
            <th>Prix / EV</th>
            {data.authenticated && <th>Exclusion</th>}
          </tr>
        </thead>
        <tbody>
          {data.items.map((item) => {
            const rec = recommendationsByItemId.get(item.item_id);
            return (
              <tr key={item.item_id}>
                <td>
                  {item.stattrak ? "StatTrak™ " : ""}
                  {item.base_name} ({item.wear})
                </td>
                <td>{item.excluded ? "Protege" : rec ? ACTION_LABELS[rec.action] : "-"}</td>
                <td>{item.excluded ? "Exclu par toi, jamais touche" : (rec?.reason ?? "-")}</td>
                <td>{rec?.price != null ? rec.price.toFixed(2) : "-"}</td>
                {data.authenticated && (
                  <td>
                    <button
                      disabled={pendingItemId === item.item_id}
                      onClick={() => toggleExclusion(item.item_id, item.excluded)}
                    >
                      {item.excluded ? "Inclure" : "Exclure"}
                    </button>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </main>
  );
}

function PortfolioChart({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  const width = 600;
  const height = 120;
  const values = snapshots.map((s) => s.total_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = snapshots
    .map((s, i) => {
      const x = (i / (snapshots.length - 1)) * width;
      const y = height - ((s.total_value - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  const latest = snapshots[snapshots.length - 1];

  return (
    <section>
      <h2>Valeur du portefeuille dans le temps</h2>
      <p>
        Dernier point : {latest.total_value.toFixed(2)} {latest.currency} (
        {new Date(latest.captured_at).toLocaleDateString()})
      </p>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label="Historique de la valeur du portefeuille"
      >
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth={2} />
      </svg>
    </section>
  );
}
