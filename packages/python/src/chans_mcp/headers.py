"""Bounded HTTP header configuration; transport negotiation stays in the SDK."""

import re

_MANAGED = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-connection",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "upgrade",
    "expect",
    "accept",
    "accept-encoding",
    "content-type",
    "last-event-id",
}
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")


def request_headers(env, extra=()):
    headers = {}
    names = set()
    size = 0

    def add(name, value, custom=False):
        nonlocal size
        if (
            not _TOKEN.fullmatch(name)
            or len(name) > 256
            or any(not 32 <= ord(c) <= 126 for c in value)
        ):
            raise ValueError(
                "Headers require valid HTTP names and printable ASCII values without control characters."
            )
        lower = name.lower()
        if custom and (lower in _MANAGED or lower.startswith("mcp-")):
            raise ValueError(
                "Headers must not override HTTP framing, routing or MCP transport headers."
            )
        if lower in names:
            raise ValueError(
                "Headers contain a duplicate name, including configured authentication headers."
            )
        size += len(name) + len(value) + 4
        if len(names) >= 64 or size > 16384:
            raise ValueError("Headers exceed the limit of 64 fields or 16 KiB.")
        names.add(lower)
        headers[name] = value

    key = env.get("CHANS_API_KEY", "").strip()
    if key:
        add("Authorization", f"Bearer {key}")
    access_id = env.get("CF_ACCESS_CLIENT_ID", "").strip()
    access_secret = env.get("CF_ACCESS_CLIENT_SECRET", "").strip()
    if access_id or access_secret:
        if not access_id or not access_secret:
            raise ValueError("CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must both be set.")
        if any(not 33 <= ord(c) <= 126 for c in access_id + access_secret):
            raise ValueError(
                "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be valid header values."
            )
        add("CF-Access-Client-Id", access_id)
        add("CF-Access-Client-Secret", access_secret)
    for header in extra:
        if len(header) > 16384:
            raise ValueError("Headers exceed the limit of 64 fields or 16 KiB.")
        name, separator, raw = header.partition(":")
        if not separator or not name:
            raise ValueError('Headers must use --header "Name: value".')
        if any(not 32 <= ord(c) <= 126 for c in raw):
            raise ValueError("Headers must not contain control characters or non-ASCII values.")
        add(name, raw.strip(), custom=True)
    if not next((v for k, v in headers.items() if k.lower() == "authorization"), None):
        raise ValueError("Set CHANS_API_KEY or provide an Authorization header.")
    return headers
