# Contribuer à CS2Trade

## Principes

- `apps/api/engine/` est le cœur déterministe : aucune dépendance à un SDK LLM, aucun appel réseau à un fournisseur d'IA. C'est ce qui garantit que l'outil reste utilisable gratuitement sans coût API variable. Toute PR qui introduit une dépendance `llm/` dans `engine/` sera refusée (vérifié par `lint-imports` en CI).
- `apps/api/engine/rules.yaml` encode la mécanique de jeu (raretés, plages d'usure, règles de trade-up). Toute modification doit être justifiée par une source primaire (patch notes Valve), pas par un blog ou un forum.
- Le module `apps/api/llm/` est optionnel et protégé par le tier premium. Il consomme uniquement les résultats d'`engine/` en lecture seule, il ne les recalcule jamais.

## Setup local

Voir le README, section "Lancer en local".

## Tests

- API : `cd apps/api && pytest`
- Lint imports : `cd apps/api && lint-imports`
- Web : `cd apps/web && npm run lint`

## Style

- Python : `ruff check .`
- Pas de commentaires narrant ce que fait le code, seulement pourquoi une contrainte non évidente existe.
