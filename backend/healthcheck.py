"""Internal readiness probe: validate DB status instead of accepting TLS redirects."""

import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

host = urlsplit(os.environ["FRONTEND_URL"]).netloc
request = Request(
    "http://127.0.0.1:8000/api/health/",
    headers={
        "Host": host,
        "X-Forwarded-Proto": "https",
    },
)
with urlopen(request, timeout=8) as response:
    payload = json.load(response)
    if response.status != 200 or payload.get("db") is not True:
        raise SystemExit(1)
