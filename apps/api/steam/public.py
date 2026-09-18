"""Import d'inventaire sans authentification : lecture publique seule.

Aucun mot de passe ni token de compte n'est jamais demande ici. Le seul
prerequis est que l'inventaire Steam soit visible publiquement au moment
de l'import (reversible ensuite par l'utilisateur).
"""

import re
from dataclasses import dataclass

import httpx

RESOLVE_VANITY_URL_ENDPOINT = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
INVENTORY_URL_TEMPLATE = "https://steamcommunity.com/inventory/{steamid64}/730/2"
INVENTORY_PAGE_SIZE = 2000
MAX_INVENTORY_PAGES = 20  # garde-fou, ~40000 items

_STEAMID64_RE = re.compile(r"^\d{17}$")
_PROFILE_URL_RE = re.compile(r"steamcommunity\.com/(profiles|id)/([^/]+)/?$")

_STATTRAK_PREFIX = "StatTrak™ "
_SOUVENIR_PREFIX = "Souvenir "
_WEAR_SUFFIX_RE = re.compile(r"^(.*) \(([^()]+)\)$")


class SteamProfileError(Exception):
    pass


class ProfileNotFoundError(SteamProfileError):
    pass


class PrivateInventoryError(SteamProfileError):
    pass


def extract_identifier(raw: str) -> str:
    """Accepte un SteamID64 brut, une URL /profiles/<id> ou /id/<vanity>, ou un vanity nu."""
    candidate = raw.strip().rstrip("/")
    match = _PROFILE_URL_RE.search(candidate)
    if match:
        return match.group(2)
    return candidate.rsplit("/", 1)[-1]


async def resolve_steam_id64(
    identifier: str, http_client: httpx.AsyncClient, steam_api_key: str
) -> str:
    if _STEAMID64_RE.match(identifier):
        return identifier

    response = await http_client.get(
        RESOLVE_VANITY_URL_ENDPOINT,
        params={"key": steam_api_key, "vanityurl": identifier},
    )
    response.raise_for_status()
    result = response.json().get("response", {})
    if result.get("success") != 1:
        raise ProfileNotFoundError(f"profil Steam introuvable pour {identifier!r}")
    return result["steamid"]


async def fetch_inventory(
    steamid64: str, http_client: httpx.AsyncClient
) -> tuple[list[dict], list[dict]]:
    url = INVENTORY_URL_TEMPLATE.format(steamid64=steamid64)
    assets: list[dict] = []
    descriptions: list[dict] = []
    start_assetid: str | None = None

    for _ in range(MAX_INVENTORY_PAGES):
        params = {"l": "english", "count": INVENTORY_PAGE_SIZE}
        if start_assetid is not None:
            params["start_assetid"] = start_assetid

        response = await http_client.get(url, params=params)
        if response.status_code == 403:
            raise PrivateInventoryError(
                "inventaire prive ou introuvable : rends-le public temporairement pour l'import"
            )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise SteamProfileError("reponse Steam invalide")

        assets.extend(payload.get("assets") or [])
        descriptions.extend(payload.get("descriptions") or [])

        if not payload.get("more_items"):
            break
        start_assetid = payload.get("last_assetid")
        if start_assetid is None:
            break

    return assets, descriptions


def _split_market_hash_name(market_hash_name: str) -> tuple[str, str, bool, bool] | None:
    name = market_hash_name
    stattrak = False
    souvenir = False
    if name.startswith(_STATTRAK_PREFIX):
        stattrak = True
        name = name[len(_STATTRAK_PREFIX) :]
    elif name.startswith(_SOUVENIR_PREFIX):
        souvenir = True
        name = name[len(_SOUVENIR_PREFIX) :]

    match = _WEAR_SUFFIX_RE.match(name)
    if not match:
        return None
    base_name, wear = match.group(1), match.group(2)
    return base_name, wear, stattrak, souvenir


@dataclass(frozen=True)
class ParsedInventoryItem:
    asset_id: str
    base_name: str
    wear: str
    stattrak: bool
    souvenir: bool
    market_hash_name: str
    tradable: bool
    marketable: bool


def parse_inventory(assets: list[dict], descriptions: list[dict]) -> list[ParsedInventoryItem]:
    descriptions_by_key = {(d["classid"], d.get("instanceid", "0")): d for d in descriptions}

    items: list[ParsedInventoryItem] = []
    for asset in assets:
        key = (asset["classid"], asset.get("instanceid", "0"))
        description = descriptions_by_key.get(key)
        if description is None:
            continue

        market_hash_name = description.get("market_hash_name", "")
        split = _split_market_hash_name(market_hash_name)
        if split is None:
            continue
        base_name, wear, stattrak, souvenir = split

        items.append(
            ParsedInventoryItem(
                asset_id=asset["assetid"],
                base_name=base_name,
                wear=wear,
                stattrak=stattrak,
                souvenir=souvenir,
                market_hash_name=market_hash_name,
                tradable=bool(description.get("tradable")),
                marketable=bool(description.get("marketable")),
            )
        )
    return items
