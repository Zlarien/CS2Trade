"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  ApiError,
  excludeItem,
  fetchInvestorAdvice,
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
    const notLoggedIn = !identifier && error.includes("authentifie");
    return (
      <main>
        <p>{notLoggedIn ? "Connecte-toi d'abord via Steam, ou importe un SteamID64." : `Erreur : ${error}`}</p>
        <Link href="/">Retour</Link>
      </main>
    );
  }

  if (!data) return null;

  const recommendationsByItemId = new Map(data.recommendations.map((r) => [r.item_id, r]));
  const sellValue = data.recommendations
    .filter((r) => r.action === "sell" && r.price != null)
    .reduce((sum, r) => sum + (r.price ?? 0), 0);
  const tradeUpCount = data.recommendations.filter((r) => r.action === "trade_up").length;

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

      <div className="summary-bar">
        <span>
          Valeur marche si vendu maintenant : <strong>{sellValue.toFixed(2)} EUR</strong>
        </span>
        {tradeUpCount > 0 && (
          <span className="muted">
            + {tradeUpCount} item(s) en trade-up recommande (EV, pas une valeur de revente)
          </span>
        )}
      </div>

      {history.length > 1 && <PortfolioChart snapshots={history} />}

      {data.authenticated && <InvestorAdviceBox />}

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

function InvestorAdviceBox() {
  const [question, setQuestion] = useState("");
  const [summary, setSummary] = useState<string | null>(null);
  const [premiumRequired, setPremiumRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    setError(null);
    setPremiumRequired(false);
    try {
      const advice = await fetchInvestorAdvice(question.trim() || undefined);
      setSummary(advice.summary);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setPremiumRequired(true);
      } else {
        setError(err instanceof Error ? err.message : "erreur inconnue");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h2>IA investisseur (premium)</h2>
      <p>
        Synthetise en langage naturel les recommandations deja calculees ci-dessous. Ne
        recalcule jamais un prix ni une probabilite.
      </p>
      <input
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="Question optionnelle, ex: par quoi je commence ?"
        aria-label="Question pour l'IA investisseur"
      />
      <button onClick={ask} disabled={loading}>
        {loading ? "..." : "Demander conseil"}
      </button>
      {premiumRequired && <p>Fonctionnalite premium, ton compte est en tier gratuit.</p>}
      {error && <p>Erreur : {error}</p>}
      {summary && <p>{summary}</p>}
    </section>
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
