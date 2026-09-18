"""OpenID 2.0 pour Steam. Pas de mot de passe ni de token OAuth : Steam
redirige vers nous avec une identite signee, qu'on reverifie aupres de
Steam avant de faire confiance au SteamID recu.
"""

import re
from urllib.parse import urlencode

import httpx

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
OPENID_NS = "http://specs.openid.net/auth/2.0"
IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"

_CLAIMED_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d{17})$")


class OpenIDVerificationError(Exception):
    pass


def build_login_url(return_to: str, realm: str) -> str:
    params = {
        "openid.ns": OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": IDENTIFIER_SELECT,
        "openid.claimed_id": IDENTIFIER_SELECT,
    }
    return f"{STEAM_OPENID_ENDPOINT}?{urlencode(params)}"


async def verify_openid_callback(
    params: dict[str, str], http_client: httpx.AsyncClient
) -> str:
    verify_params = dict(params)
    verify_params["openid.mode"] = "check_authentication"

    response = await http_client.post(STEAM_OPENID_ENDPOINT, data=verify_params)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise OpenIDVerificationError(
            f"Steam a repondu {response.status_code} pendant la verification"
        ) from exc
    if "is_valid:true" not in response.text:
        raise OpenIDVerificationError("signature OpenID refusee par Steam")

    claimed_id = params.get("openid.claimed_id", "")
    match = _CLAIMED_ID_RE.match(claimed_id)
    if not match:
        raise OpenIDVerificationError(f"claimed_id Steam invalide : {claimed_id!r}")
    return match.group(1)
