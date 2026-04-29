"""POST XML to a running TallyPrime instance (HTTP server on port 9000).

Enable in Tally: F1 Help > Settings > Connectivity > Client/Server config
> TallyPrime acts as Both / Server, port 9000.
"""
from __future__ import annotations
import urllib.request

from tmv_recon.config import TALLY_HOST, TALLY_PORT


def post_xml(xml: str, *, host: str | None = None, port: int | None = None, timeout: int = 60) -> str:
    url = f"http://{host or TALLY_HOST}:{port or TALLY_PORT}"
    req = urllib.request.Request(
        url, data=xml.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")
