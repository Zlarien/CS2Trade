# CS2Trade

Outil qui analyse ton inventaire CS2 (Counter-Strike 2) et recommande, item par item, de garder, vendre ou faire un trade-up contract, pour faire croitre la valeur totale de l'inventaire. Le calcul (espérance de gain des trade-up, valorisation) est entièrement déterministe, aucune IA n'est nécessaire pour l'usage de base.

## Statut

Scaffolding en place, aucune fonctionnalité branchée encore. Voir `apps/api/engine/` pour le cœur de calcul (déterministe) à venir.

## Structure

- `apps/web` : Next.js, présentation uniquement.
- `apps/api` : FastAPI (Python). `engine/` est le cœur de calcul, sans dépendance IA. `llm/` est un module optionnel (tier premium) isolé, il ne modifie jamais un calcul, il synthétise en langage naturel les résultats d'`engine/`.
- `infra/docker-compose.yml` : postgres, redis, api, web.

## Lancer en local

```
cp .env.example .env
# renseigner STEAM_API_KEY (gratuit, https://steamcommunity.com/dev/apikey)
docker compose -f infra/docker-compose.yml up
```

## Import de l'inventaire

Deux modes, aucun ne nécessite de partager ton mot de passe Steam :

1. **Connexion Steam (OpenID)** : synchronisation automatique et continue, tu peux exclure des items que l'outil ne doit jamais toucher.
2. **Import manuel par SteamID/URL de profil** : lecture ponctuelle de l'inventaire public, sans connexion ni token stocké. Si ton profil est privé, un formulaire manuel existe en secours.

## Licence

MIT, voir `LICENSE`.
