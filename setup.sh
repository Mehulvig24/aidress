#!/usr/bin/env bash
# setup.sh — One-command installer for PACT demo aliases on macOS
#
# Adds curl shortcuts for every PACT endpoint to ~/.zshrc so developers
# can explore the live API without writing any curl commands themselves.
#
# Safe to run multiple times — checks for each alias before adding it,
# so nothing is duplicated on a second run.
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
#   — or —
#   bash setup.sh

set -euo pipefail

ZSHRC="$HOME/.zshrc"
BASE="https://pact-protocol.onrender.com"

# ── Helper: append alias only if the alias name is not already in ~/.zshrc ──

add_alias() {
    local name="$1"   # alias name, e.g. pact-wake
    local cmd="$2"    # full shell command the alias expands to

    # grep -q returns 0 if found — skip if any line already defines this alias
    if grep -q "alias ${name}=" "$ZSHRC" 2>/dev/null; then
        echo "  [skip]  $name already exists"
    else
        # Escape any bare " in cmd to \" so the alias is valid inside double quotes.
        # printf is used instead of echo to avoid interpreting backslash sequences.
        local escaped_cmd="${cmd//\"/\\\"}"
        printf 'alias %s="%s"\n' "$name" "$escaped_cmd" >> "$ZSHRC"
        echo "  [added] $name"
    fi
}


# ── Section header printed during install for readability ───────────────────

section() {
    echo ""
    echo "── $1"
}


# ── Begin install ────────────────────────────────────────────────────────────

echo ""
echo "PACT — Installing aliases into $ZSHRC"
echo "══════════════════════════════════════════════"


# ── Wake + Network ───────────────────────────────────────────────────────────
# pact-wake is a raw curl with no pretty-print — intentionally fast, used to
# warm up Render's free-tier server before running any other commands.

section "Wake + Network"

add_alias "pact-wake" \
    "curl -s ${BASE}/registry"

add_alias "pact-registry" \
    "curl -s ${BASE}/registry | python3 -m json.tool"


# ── Verify ───────────────────────────────────────────────────────────────────
# Covers all three trust outcomes: proceed (score 88), abort (low-trust flag),
# and unregistered (no record at all). pact-verify-registered checks the agent
# created by pact-register so demos can be run end-to-end in sequence.

section "Verify"

add_alias "pact-verify-good" \
    "curl -s -X POST ${BASE}/verify -H 'Content-Type: application/json' -d '{\"agent_id\": \"agent_freightbot_01\"}' | python3 -m json.tool"

add_alias "pact-verify-flagged" \
    "curl -s -X POST ${BASE}/verify -H 'Content-Type: application/json' -d '{\"agent_id\": \"agent_riskroute_01\"}' | python3 -m json.tool"

add_alias "pact-verify-unknown" \
    "curl -s -X POST ${BASE}/verify -H 'Content-Type: application/json' -d '{\"agent_id\": \"unknown-agent-999\"}' | python3 -m json.tool"

add_alias "pact-verify-registered" \
    "curl -s -X POST ${BASE}/verify -H 'Content-Type: application/json' -d '{\"agent_id\": \"demo-agent-001\"}' | python3 -m json.tool"


# ── Agent Profile ────────────────────────────────────────────────────────────
# Full record including all ratings received — useful for showing the
# ratings_received array and routing block in a demo.

section "Agent Profile"

add_alias "pact-agent-freightbot" \
    "curl -s ${BASE}/agent/agent_freightbot_01 | python3 -m json.tool"

add_alias "pact-agent-shipchain" \
    "curl -s ${BASE}/agent/agent_shipchain_01 | python3 -m json.tool"

add_alias "pact-agent-cargovfy" \
    "curl -s ${BASE}/agent/agent_cargovfy_01 | python3 -m json.tool"


# ── Discovery ────────────────────────────────────────────────────────────────
# /match returns verified agents (score >= 50) that have ALL listed capabilities,
# ranked by trust_score descending — best option is always first in the array.

section "Discovery"

add_alias "pact-match-freight" \
    "curl -s -X POST ${BASE}/match -H 'Content-Type: application/json' -d '{\"required_capabilities\": [\"freight_booking\", \"customs_clearance\"]}' | python3 -m json.tool"

add_alias "pact-match-routing" \
    "curl -s -X POST ${BASE}/match -H 'Content-Type: application/json' -d '{\"required_capabilities\": [\"route_optimisation\", \"last_mile_delivery\"]}' | python3 -m json.tool"

add_alias "pact-match-customs" \
    "curl -s -X POST ${BASE}/match -H 'Content-Type: application/json' -d '{\"required_capabilities\": [\"customs_clearance\", \"compliance_check\"]}' | python3 -m json.tool"


# ── Register ─────────────────────────────────────────────────────────────────
# Creates demo-agent-001 with a starting trust_score of 40 (pending review).
# Returns 409 if the agent_id or org_domain is already taken — idempotent to run.

section "Register"

add_alias "pact-register" \
    "curl -s -X POST ${BASE}/register -H 'Content-Type: application/json' -d '{\"agent_id\": \"demo-agent-001\", \"org_name\": \"Demo Corp\", \"org_domain\": \"democorp.com\", \"contact_email\": \"demo@democorp.com\"}' | python3 -m json.tool"


# ── Rating — valid ───────────────────────────────────────────────────────────
# Submits a score-5 rating from freightbot_01 (score 88, qualifies as rater)
# to shipchain_01. Uses transaction_id txn-demo-001.

section "Rating — valid"

add_alias "pact-rate-valid" \
    "curl -s -X POST ${BASE}/rate -H 'Content-Type: application/json' -d '{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-001\"}' | python3 -m json.tool"


# ── Rating — anti-gaming demos ───────────────────────────────────────────────
# Each of these should return HTTP 403 with a specific rule violation message:
#   pact-rate-self    → Rule D: cannot rate yourself
#   pact-rate-dupe    → Rule C: txn-demo-001 already used above
#   pact-rate-blocked → Rule A: agent_riskroute_01 is not in the registry (404)
#                       or has trust_score < 50 (403) — both mean blocked

section "Rating — anti-gaming"

add_alias "pact-rate-self" \
    "curl -s -X POST ${BASE}/rate -H 'Content-Type: application/json' -d '{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_freightbot_01\", \"score\": 5, \"transaction_id\": \"txn-demo-002\"}' | python3 -m json.tool"

add_alias "pact-rate-dupe" \
    "curl -s -X POST ${BASE}/rate -H 'Content-Type: application/json' -d '{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-001\"}' | python3 -m json.tool"

add_alias "pact-rate-blocked" \
    "curl -s -X POST ${BASE}/rate -H 'Content-Type: application/json' -d '{\"rater_agent_id\": \"agent_riskroute_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-003\"}' | python3 -m json.tool"


# ── Reload shell config so aliases are live immediately ─────────────────────

echo ""
echo "── Reloading ~/.zshrc"
# shellcheck disable=SC1090  — path is intentionally dynamic
source "$ZSHRC"


# ── Confirmation ─────────────────────────────────────────────────────────────

echo ""
echo "PACT — Setup Complete"
echo "══════════════════════════════════════════════"
echo ""
echo "NETWORK"
echo "  pact-wake              Wake up Render server"
echo "  pact-registry          See all trusted agents on the network"
echo ""
echo "VERIFY"
echo "  pact-verify-good       Verify trusted agent (FreightBot, score 88)"
echo "  pact-verify-flagged    Verify flagged agent (low score, blocked)"
echo "  pact-verify-unknown    Verify unknown agent (not on network)"
echo "  pact-verify-registered Verify agent you just registered"
echo ""
echo "DISCOVER"
echo "  pact-match-freight     Find agents for freight + customs"
echo "  pact-match-routing     Find agents for routing + last mile"
echo "  pact-match-customs     Find agents for customs + compliance"
echo ""
echo "AGENT PROFILE"
echo "  pact-agent-freightbot  Full profile — FreightBot Logistics"
echo "  pact-agent-shipchain   Full profile — ShipChain Protocol"
echo "  pact-agent-cargovfy    Full profile — CargoVerify Inc"
echo ""
echo "REGISTER"
echo "  pact-register          Register a new agent on the network"
echo ""
echo "RATING"
echo "  pact-rate-valid        Submit a valid rating"
echo "  pact-rate-self         Attempt self rating (blocked)"
echo "  pact-rate-dupe         Attempt duplicate rating (blocked)"
echo "  pact-rate-blocked      Unregistered agent attempts rating (blocked)"
echo ""
echo "══════════════════════════════════════════════"
echo "PACT is live at ${BASE}"
echo "Start with: pact-wake → pact-registry → pact-verify-good"
echo "══════════════════════════════════════════════"
echo ""
