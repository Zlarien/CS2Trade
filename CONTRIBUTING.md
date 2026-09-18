# Contribuer à CS2Trade

## Principes

- `apps/api/engine/` est le cœur déterministe : aucune dépendance à un SDK LLM, aucun appel réseau à un fournisseur d'IA. C'est ce qui garantit que l'outil reste utilisable gratuitement sans coût API variable. Toute PR qui introduit une dépendance `llm/` dans `engine/` sera refusée (vérifié par `lint-imports` en CI).
- `apps/api/engine/rules.yaml` encode la mécanique de jeu (raretés, plages d'usure, règles de trade-up). Toute modification doit être justifiée par une source primaire (patch notes Valve), pas par un blog ou un forum.
- Le module `apps/api/llm/` est optionnel et protégé par le tier premium (`require_premium_tier`). Il consomme uniquement les résultats d'`engine/` en lecture seule, il ne les recalcule jamais.
- **Caisses (cases) : jamais un conseil d'investissement.** `refdata/` ne vendore que `skins.json`/`collections.json`, volontairement sans `cases.json` : l'outil ne peut donc pas recommander d'ouvrir, garder ou acheter une caisse comme stratégie, seulement chiffrer un skin déjà en inventaire. N'ajoutez `cases.json` que pour du pricing informatif (valeur de revente de la caisse elle-même), jamais pour générer une recommandation `sell`/`trade_up`/`hold` sur le contenu potentiel d'une caisse non ouverte.

## Modules

| Dossier | Rôle |
|---|---|
| `engine/` | Calcul déterministe : valorisation, EV des trade-up, recommandations. |
| `pricing/` | Adaptateurs de prix (Skinport, Steam Market), interface `PriceSource` commune. |
| `refdata/` | Snapshot vendoré des skins/collections (ByMykel/CSGO-API), script de rafraîchissement. |
| `steam/` | Client Steam public : résolution SteamID, inventaire, parsing. Aucune authentification. |
| `auth/` | OpenID Steam et sessions Redis. Jamais de mot de passe ni de token Steam stocké. |
| `db/` | Modèles SQLAlchemy (users, exclusions, historique), sync du portefeuille. |
| `llm/` | IA investisseur, premium uniquement, isolé d'`engine/`. |
| `routers/` | Endpoints FastAPI, composent les modules ci-dessus. |
| `scripts/` | Outils opérateur (sync quotidienne, changement de tier) : jamais des routes publiques. |

## Setup local

Voir le README, section "Lancer en local".

## Tests

- API : `cd apps/api && pytest`
- Lint imports : `cd apps/api && lint-imports`
- Web : `cd apps/web && npm run lint`

## Style

- Python : `ruff check .`
- Pas de commentaires narrant ce que fait le code, seulement pourquoi une contrainte non évidente existe.
