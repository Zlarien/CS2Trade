import httpx
import pytest

from auth.openid import OpenIDVerificationError, build_login_url, verify_openid_callback

VALID_CLAIMED_ID = "https://steamcommunity.com/openid/id/76561198034202275"


def _client_with_handler(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_build_login_url_contains_expected_params() -> None:
    url = build_login_url(
        return_to="http://localhost:8000/auth/steam/callback", realm="http://localhost:8000"
    )
    assert url.startswith("https://steamcommunity.com/openid/login?")
    assert "openid.mode=checkid_setup" in url
    assert "openid.return_to=http" in url
    assert "identifier_select" in url


@pytest.mark.asyncio
async def test_verify_openid_callback_accepts_valid_signature() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "openid.mode=check_authentication" in request.content.decode()
        return httpx.Response(200, text="ns:http://specs.openid.net/auth/2.0\nis_valid:true\n")

    params = {"openid.claimed_id": VALID_CLAIMED_ID, "openid.mode": "id_res"}
    steamid64 = await verify_openid_callback(params, _client_with_handler(handler))
    assert steamid64 == "76561198034202275"


@pytest.mark.asyncio
async def test_verify_openid_callback_rejects_invalid_signature() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ns:http://specs.openid.net/auth/2.0\nis_valid:false\n")

    params = {"openid.claimed_id": VALID_CLAIMED_ID, "openid.mode": "id_res"}
    with pytest.raises(OpenIDVerificationError, match="refusee"):
        await verify_openid_callback(params, _client_with_handler(handler))


@pytest.mark.asyncio
async def test_verify_openid_callback_rejects_malformed_claimed_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="is_valid:true\n")

    params = {"openid.claimed_id": "not-a-steam-url", "openid.mode": "id_res"}
    with pytest.raises(OpenIDVerificationError, match="claimed_id"):
        await verify_openid_callback(params, _client_with_handler(handler))
