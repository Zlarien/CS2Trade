# CS2Trade

Outil qui analyse ton inventaire CS2 (Counter-Strike 2) et recommande, item par item, de garder, vendre ou faire un trade-up contract, pour faire croitre la valeur totale de l'inventaire. Le calcul (espérance de gain des trade-up, valorisation) est entièrement déterministe, aucune IA n'est nécessaire pour l'usage de base.

## Statut

Moteur de calcul, import Steam (public et OpenID), recommandations, exclusions, historique de portefeuille, tiering premium et IA investisseur fonctionnels et testés. UI Next.js minimale branchée (`apps/web`). Voir `apps/api/engine/` pour le cœur de calcul (déterministe).

**Limite connue** : Steam n'expose jamais le float exact d'un item via ses APIs publiques (inventaire ou OpenID) sans un inspect link + connexion au Game Coordinator, hors scope V1. Le moteur travaille donc sur un float approximé (milieu de la plage d'usure), toujours signalé via `float_is_estimated: true` dans les reponses.

## Structure

- `apps/web` : Next.js, présentation uniquement.
- `apps/api` : FastAPI (Python). `engine/` est le cœur de calcul, sans dépendance IA. `llm/` est un module optionnel (tier premium) isolé, il ne modifie jamais un calcul, il synthétise en langage naturel les résultats d'`engine/`.
- `infra/docker-compose.yml` : postgres, redis, api, web.

## Lancer en local

```
cp .env.example .env
# renseigner STEAM_API_KEY (gratuit, https://steamcommunity.com/dev/apikey)
docker compose -f infra/docker-compose.yml up
python -m db.init_db   # cree le schema (users, excluded_items, inventory_snapshots)
```

L'API expose sa doc interactive sur `/docs`.

## Import de l'inventaire

Deux modes, aucun ne nécessite de partager ton mot de passe Steam :

1. **Connexion Steam (OpenID)**, `GET /auth/steam/login` : synchronisation automatique (`GET /inventory/me/recommendations`), tu peux exclure des items via `POST /me/excluded-items` que l'outil ne doit jamais toucher.
2. **Import manuel par SteamID/URL de profil**, `GET /inventory/recommendations?identifier=...` : lecture ponctuelle de l'inventaire public, sans connexion ni token stocké. Si ton profil est privé, un formulaire manuel existe en secours.

## Historique de la valeur du portefeuille

`python -m scripts.daily_sync` recalcule la valeur totale de l'inventaire de chaque utilisateur lié et l'ajoute à `inventory_snapshots`. Pas de scheduler embarqué en V1 : à brancher sur un cron du self-hoster.

## IA investisseur (premium)

`POST /me/investor-advice` synthétise en langage naturel les recommandations déjà calculées par `engine/` (jamais l'inverse : voir `llm/investor.py`). Nécessite `ANTHROPIC_API_KEY` et un compte en tier `premium`. Aucune route publique pour passer premium soi-même tant qu'aucune facturation n'est branchée : `python -m scripts.set_tier <steamid64> premium` est le seul levier, réservé à l'opérateur du self-host.

## Licence

MIT, voir `LICENSE`.
