# aidress_sdk.py — Lightweight Aidress client SDK
#
# Drop this single file into any Python project to add Aidress trust verification.
# The simplest possible integration is two lines:
#
#   from aidress_sdk import verify
#   trust = verify("agent_id_here")
#
# No dependencies beyond Python's standard library.

import urllib.request
import urllib.error
import json
import ssl
import time

# ── SSL context ──────────────────────────────────────────────────────────────
# macOS Python 3.x does not use the system certificate store by default.
# This context skips certificate verification so the SDK works out of the box
# on any machine without extra setup steps.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode    = ssl.CERT_NONE

# The error object returned whenever PACT is unreachable or returns an
# unexpected response — safe defaults so callers can always read trust_score.
_UNREACHABLE = {"error": "Aidress unreachable", "verified": False, "trust_score": 0}


def _parse_body(raw_bytes: bytes, status_code: int) -> dict:
    """
    Safely decode an HTTP response body to a dict.
    Falls back to a plain error dict if the body is empty or non-JSON
    (e.g. an HTML gateway error page from a hosting proxy).
    """
    raw = raw_bytes.decode("utf-8", errors="replace").strip()
    if not raw:
        return {"detail": f"HTTP {status_code} (empty body)"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Non-JSON body (HTML error page, plain text, etc.)
        return {"detail": f"HTTP {status_code} — non-JSON response from server"}


# ── PACTClient ────────────────────────────────────────────────────────────────

class PACTClient:
    """
    A thin wrapper around the PACT REST API.

    Create one instance per agent and reuse it across calls:
        client = PACTClient()                          # uses live Render URL
        client = PACTClient("http://localhost:8001")   # points at local server
    """

    def __init__(self, base_url: str = "https://aidress.onrender.com"):
        # Strip trailing slash so callers don't need to worry about formatting
        self.base_url = base_url.rstrip("/")

    # ── Core request method ──────────────────────────────────────────────────

    def _post(self, path: str, payload: dict, _retries: int = 7) -> tuple[int, dict]:
        """
        Send a POST request to the PACT API and return (status_code, body).
        Retries up to 7 times on 503 — Render free-tier cold starts can take
        up to 60 seconds; we wait 5s between attempts (35s total headroom).
        """
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url=f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(1, _retries + 1):
            try:
                with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
                    return resp.status, json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = _parse_body(e.read(), e.code)
                # 503 means the host is still waking up — wait and retry
                if e.code == 503 and attempt < _retries:
                    print(f"  [Aidress] Server warming up, retrying ({attempt}/{_retries - 1})…")
                    time.sleep(5)
                    continue
                return e.code, body
            except urllib.error.URLError:
                # Network error, DNS failure, timeout, etc.
                return 0, dict(_UNREACHABLE)
        return 503, {"detail": "Server unavailable after retries"}

    def _get(self, path: str) -> tuple[int, dict | list]:
        """Send a GET request to the PACT API and return (status_code, body)."""
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, _parse_body(e.read(), e.code)
        except urllib.error.URLError:
            return 0, dict(_UNREACHABLE)

    # ── Public methods ───────────────────────────────────────────────────────

    def verify(self, agent_id: str) -> dict:
        """
        Look up an agent's trust profile before transacting with it.

        Returns a trust object with fields: agent_id, verified, trust_score,
        flags, capabilities, routing, org_name, org_domain.
        Always returns a dict — never raises.

        Usage:
            trust = client.verify("agent_freightbot_01")
            if trust["trust_score"] >= 70:
                proceed()
        """
        status, body = self._post("/verify", {"agent_id": agent_id})
        if status == 0:
            # PACT was unreachable — return a safe, low-trust default
            return {**_UNREACHABLE, "agent_id": agent_id}
        return body

    def match(self, required_capabilities: list[str]) -> list[dict]:
        """
        Find verified agents that have all the capabilities you need,
        ranked by trust_score descending (best match first).

        Returns a list of trust objects — empty list if nothing matches.

        Usage:
            agents = client.match(["freight_booking", "customs_clearance"])
            best   = agents[0] if agents else None
        """
        status, body = self._post("/match", {"required_capabilities": required_capabilities})
        if status == 0 or not isinstance(body, list):
            # Unreachable or unexpected shape — return empty list so callers
            # can safely do `agents[0]` with a guard rather than catching exceptions
            return []
        return body

    def rate(
        self,
        rater_agent_id: str,
        rated_agent_id: str,
        score:          int,
        transaction_id: str,
    ) -> dict:
        """
        Submit a 1-5 trust rating after completing a transaction.

        Returns the updated trust object for the rated agent on success,
        or a dict with an "error" key if the rating was blocked.

        Usage:
            result = client.rate("agent_a", "agent_b", score=5, transaction_id="txn-xyz")
        """
        status, body = self._post("/rate", {
            "rater_agent_id": rater_agent_id,
            "rated_agent_id": rated_agent_id,
            "score":          score,
            "transaction_id": transaction_id,
        })
        if status == 0:
            return dict(_UNREACHABLE)
        if status == 403:
            # Anti-gaming rule triggered — surface the reason clearly
            return {"error": body.get("detail", "Rating blocked by PACT anti-gaming rules")}
        return body

    def register(
        self,
        agent_id:      str,
        org_name:      str,
        org_domain:    str,
        contact_email: str,
    ) -> dict:
        """
        Register a new agent with the PACT registry.

        Returns a confirmation dict with status "pending_review" on success,
        or a dict with an "error" key if the agent_id or org_domain is taken.

        Usage:
            result = client.register("my_agent_01", "Acme Corp", "acme.com", "bot@acme.com")
        """
        status, body = self._post("/register", {
            "agent_id":      agent_id,
            "org_name":      org_name,
            "org_domain":    org_domain,
            "contact_email": contact_email,
        })
        if status == 0:
            return dict(_UNREACHABLE)
        if status == 409:
            # Duplicate agent_id or org_domain
            return {"error": body.get("detail", "Agent or domain already registered")}
        return body


# ── Module-level convenience functions ───────────────────────────────────────
# These are the one-liners developers can import directly without instantiating
# a client. They use a shared default client pointed at the live Render URL.

_default_client = PACTClient()


def verify(agent_id: str) -> dict:
    """
    Look up an agent's trust profile — the single line you add to your agent.

    from aidress_sdk import verify
    trust = verify("agent_id_here")
    """
    return _default_client.verify(agent_id)


def match(required_capabilities: list[str]) -> list[dict]:
    """
    Find trusted agents that can handle the capabilities you need.

    from aidress_sdk import match
    agents = match(["freight_booking", "customs_clearance"])
    """
    return _default_client.match(required_capabilities)


def rate(
    rater_agent_id: str,
    rated_agent_id: str,
    score:          int,
    transaction_id: str,
) -> dict:
    """
    Submit a trust rating after a transaction.

    from aidress_sdk import rate
    rate("agent_a", "agent_b", score=5, transaction_id="txn-xyz")
    """
    return _default_client.rate(rater_agent_id, rated_agent_id, score, transaction_id)


def register(
    agent_id:      str,
    org_name:      str,
    org_domain:    str,
    contact_email: str,
) -> dict:
    """
    Register a new agent with PACT.

    from aidress_sdk import register
    register("my_agent_01", "Acme Corp", "acme.com", "bot@acme.com")
    """
    return _default_client.register(agent_id, org_name, org_domain, contact_email)


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═" * 55)
    print("  Aidress SDK — integration demo")
    print("═" * 55)

    # ── verify() ─────────────────────────────────────────────────────────────
    print("\n── verify('agent_freightbot_01') ──")
    print("  from aidress_sdk import verify")
    print("  trust = verify('agent_freightbot_01')\n")

    trust = verify("agent_freightbot_01")

    print(f"  agent_id    : {trust.get('agent_id')}")
    print(f"  org_name    : {trust.get('org_name')}")
    print(f"  verified    : {trust.get('verified')}")
    print(f"  trust_score : {trust.get('trust_score')}/100")
    print(f"  capabilities: {trust.get('capabilities', [])}")
    print(f"  flags       : {trust.get('flags', []) or 'none'}")

    # ── match() ───────────────────────────────────────────────────────────────
    print("\n── match(['freight_booking']) ──")
    print("  from aidress_sdk import match")
    print("  agents = match(['freight_booking'])\n")

    agents = match(["freight_booking"])

    if agents:
        best = agents[0]
        print(f"  {len(agents)} agent(s) matched. Top result:")
        print(f"    agent_id    : {best.get('agent_id')}")
        print(f"    org_name    : {best.get('org_name')}")
        print(f"    trust_score : {best.get('trust_score')}/100")
        print(f"    capabilities: {best.get('capabilities', [])}")
    else:
        print("  No agents matched.")

    print("\n" + "═" * 55)
    print("  Two imports, two calls. That's the full Aidress integration.")
    print("═" * 55 + "\n")
