# demo_agent.py — Simulates a real AI agent using Aidress to vet counterparts before transacting.
#
# The core idea: before an agent does any work with an unknown counterpart,
# it calls pact_verify() to get a trust score. One function call. That's it.
#
# Run this file directly:  python demo_agent.py

import urllib.request
import urllib.error
import json

PACT_BASE_URL = "https://api.aidress.ai"


# ── Core integration function ────────────────────────────────────────────────

def pact_verify(agent_id: str) -> dict:
    """
    THE one-liner a developer adds to their agent.
    Sends agent_id to PACT and returns a trust object with score, flags, and identity.
    """
    payload = json.dumps({"agent_id": agent_id}).encode("utf-8")
    req = urllib.request.Request(
        url=f"{PACT_BASE_URL}/verify",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        # If PACT itself is unreachable, fail safe — treat as untrusted
        print(f"  [!] Could not reach Aidress server: {e.reason}")
        return {
            "agent_id":    agent_id,
            "verified":    False,
            "trust_score": 0,
            "flags":       ["pact_unreachable"],
            "org_name":    None,
        }


# ── Transaction decision engine ──────────────────────────────────────────────

def simulate_transaction(agent_id: str, task: str) -> dict:
    """
    Attempts a task with a counterpart agent after first checking PACT.
    Returns a result object describing the decision made and why.
    """
    print(f"  Task   : {task}")
    print(f"  Counterpart: {agent_id}")
    print()

    # ── Step 1: verify the counterpart via PACT ──────────────────────────────
    trust = pact_verify(agent_id)

    score     = trust.get("trust_score", 0)
    verified  = trust.get("verified", False)
    flags     = trust.get("flags", [])
    org_name  = trust.get("org_name") or "Unknown organisation"

    print(f"  Aidress response:")
    print(f"    Organisation : {org_name}")
    print(f"    Verified     : {'Yes' if verified else 'No'}")
    print(f"    Trust score  : {score}/100")
    print(f"    Flags        : {', '.join(flags) if flags else 'None'}")
    print()

    # ── Step 2: apply the trust decision rules ───────────────────────────────

    if score >= 70:
        # High trust — proceed normally
        decision = "proceed"
        reason   = f"Trust score {score}/100 exceeds the confidence threshold. Transaction authorised."
        _print_decision("PROCEED", reason, color="green")

    elif score >= 40:
        # Medium trust — proceed but flag for human review
        decision = "caution"
        reason   = (
            f"Trust score {score}/100 is acceptable but below the high-confidence threshold. "
            "Proceeding with reduced transaction limits and logging for review."
        )
        _print_decision("CAUTION — PROCEEDING WITH LIMITS", reason, color="yellow")

    else:
        # Low trust or completely unregistered — do not transact
        decision = "abort"
        if "unregistered" in flags:
            reason = (
                f"Agent '{agent_id}' has no PACT record. "
                "Cannot verify identity or trust history. Transaction blocked."
            )
        elif "pact_unreachable" in flags:
            reason = "PACT registry is unreachable. Failing safe — transaction blocked."
        else:
            flag_detail = ", ".join(flags) if flags else "low trust score"
            reason = (
                f"Trust score {score}/100 is below the minimum threshold. "
                f"Flags on record: {flag_detail}. Transaction blocked."
            )
        _print_decision("ABORT", reason, color="red")

    return {
        "agent_id":    agent_id,
        "decision":    decision,
        "trust_score": score,
        "reason":      reason,
    }


# ── Output helpers ───────────────────────────────────────────────────────────

# ANSI colour codes for terminal output (ignored if terminal doesn't support them)
_COLOURS = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "reset": "\033[0m"}

def _print_decision(label: str, reason: str, color: str) -> None:
    """Print the final decision in a coloured, easy-to-read block."""
    c = _COLOURS.get(color, "")
    r = _COLOURS["reset"]
    print(f"  {c}Decision : {label}{r}")
    print(f"  Reason   : {reason}")

def _separator(title: str) -> None:
    """Print a labelled divider between scenarios."""
    line = "─" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}")


# ── Demo scenarios ───────────────────────────────────────────────────────────

def main():
    """Run four scenarios that illustrate every trust outcome PACT can return."""

    print("\n" + "═" * 60)
    print("  Aidress DEMO — AI Discovery, Reputation, Exchange & Settlement System")
    print("  Simulating an AI agent vetting counterparts before work")
    print("═" * 60)

    # ── Scenario 1: high-trust agent ─────────────────────────────────────────
    _separator("Scenario 1 of 4 — High-trust counterpart")
    simulate_transaction(
        agent_id="agent_freightbot_01",
        task="Route 48 pallets from Rotterdam to Chicago via air freight",
    )

    # ── Scenario 2: medium-trust agent ───────────────────────────────────────
    _separator("Scenario 2 of 4 — Medium-trust counterpart")
    simulate_transaction(
        agent_id="agent_routeiq_01",
        task="Optimise last-mile delivery schedule for 12 drop points",
    )

    # ── Scenario 3: low-trust / flagged agent ─────────────────────────────────
    # agent_riskroute_01 is not in the PACT registry — PACT returns trust_score 0
    # and the "unregistered" flag, which triggers an abort. A registered but
    # flagged agent (e.g. agent_fakecargo_77, score 8) would follow the same path.
    _separator("Scenario 3 of 4 — Flagged / low-trust counterpart")
    simulate_transaction(
        agent_id="agent_riskroute_01",
        task="Handle customs clearance for a high-value electronics shipment",
    )

    # ── Scenario 4: completely unknown agent ──────────────────────────────────
    _separator("Scenario 4 of 4 — Completely unknown counterpart")
    simulate_transaction(
        agent_id="unknown-agent-999",
        task="Negotiate spot freight rates on behalf of client",
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  Demo complete.")
    print()
    print("  This is what Aidress adds to any AI agent:")
    print("    trust = pact_verify(counterpart_agent_id)")
    print()
    print("  One call. Verified identity. Informed decision.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
