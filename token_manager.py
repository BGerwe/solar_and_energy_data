"""Manages Enphase JWT token caching and refresh."""

import json
import os

from enphase_api.cloud.authentication import Authentication

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "configuration", "token.json")


def _save_token(token, serial_number):
    """Write token and serial number to disk."""
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"token": token, "serial_number": serial_number}, f)


def _load_token():
    """Read cached token from disk. Returns (token, serial_number) or (None, None)."""
    if not os.path.exists(TOKEN_PATH):
        return None, None
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("token"), data.get("serial_number")


def get_valid_token(username, password, serial_number):
    """Return a valid JWT token, refreshing from Enphase cloud if the cached one is expired.

    Args:
        username: Enphase account email.
        password: Enphase account password.
        serial_number: IQ Gateway serial number.

    Returns:
        A valid JWT token string.
    """
    token, cached_serial = _load_token()

    if (
        token
        and cached_serial == serial_number
        and Authentication.check_token_valid(
            token=token, gateway_serial_number=serial_number
        )
    ):
        return token

    # Token missing, expired, or wrong serial — refresh.
    auth = Authentication()
    auth.authenticate(username, password)
    token = auth.get_token_for_commissioned_gateway(serial_number)

    _save_token(token, serial_number)
    return token
