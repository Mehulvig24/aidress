#!/usr/bin/env bash
# setup.sh — One-command installer for PACT demo aliases on macOS
#
# Writes curl shortcuts for every PACT endpoint into ~/.zshrc so developers
# can explore the live API without writing any curl commands themselves.
#
# Idempotent: removes all existing pact- aliases before re-writing, so running
# this script a second time produces a clean, duplicate-free result.
#
# Usage:
#   bash setup.sh

set -euo pipefail

ZSHRC="$HOME/.zshrc"
BASE="https://pact-protocol.onrender.com"

echo ""
echo "PACT — Installer"
echo "══════════════════════════════════════════════"
echo ""

# ── Step 1: Remove any existing pact- aliases ────────────────────────────────
# Deletes every line containing "pact-" so re-runs don't accumulate duplicates.

echo "Removing existing pact- aliases from $ZSHRC ..."
sed -i '' '/pact-/d' "$ZSHRC"
echo "  [done]"
echo ""

# ── Step 2: Append all aliases via a quoted-delimiter heredoc ────────────────
# <<'EOF' (quoted delimiter) means the heredoc body is treated as a literal
# string — zero variable expansion, zero quote interpretation by bash.
# This guarantees that every alias is written exactly as typed, with the
# correct quoting pattern:
#
#   alias name='curl ... -H "Content-Type: application/json" -d "{\"key\": \"val\"}"'
#
# Single quotes wrap the whole command (safe for the shell to store the alias).
# Double quotes wrap the header value and JSON body.
# \" inside the JSON body becomes " when the alias is actually invoked.

echo "Writing aliases to $ZSHRC ..."

cat >> "$ZSHRC" << 'EOF'

# ── PACT aliases ─────────────────────────────────────────────────────────────

# Wake + Network
alias pact-wake='curl -s https://pact-protocol.onrender.com/registry'
alias pact-registry='curl -s https://pact-protocol.onrender.com/registry | python3 -m json.tool'

# Verify
alias pact-verify-good='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"agent_freightbot_01\"}" | python3 -m json.tool'
alias pact-verify-flagged='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"agent_riskroute_01\"}" | python3 -m json.tool'
alias pact-verify-unknown='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"unknown-agent-999\"}" | python3 -m json.tool'
alias pact-verify-registered='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"demo-agent-001\"}" | python3 -m json.tool'

# Agent Profile
alias pact-agent-freightbot='curl -s https://pact-protocol.onrender.com/agent/agent_freightbot_01 | python3 -m json.tool'
alias pact-agent-shipchain='curl -s https://pact-protocol.onrender.com/agent/agent_shipchain_01 | python3 -m json.tool'
alias pact-agent-cargovfy='curl -s https://pact-protocol.onrender.com/agent/agent_cargovfy_01 | python3 -m json.tool'

# Discovery
alias pact-match-freight='curl -s -X POST https://pact-protocol.onrender.com/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"freight_booking\", \"customs_clearance\"]}" | python3 -m json.tool'
alias pact-match-routing='curl -s -X POST https://pact-protocol.onrender.com/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"route_optimisation\", \"last_mile_delivery\"]}" | python3 -m json.tool'
alias pact-match-customs='curl -s -X POST https://pact-protocol.onrender.com/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"customs_clearance\", \"compliance_check\"]}" | python3 -m json.tool'

# Register
alias pact-register='curl -s -X POST https://pact-protocol.onrender.com/register -H "Content-Type: application/json" -d "{\"agent_id\": \"demo-agent-001\", \"org_name\": \"Demo Corp\", \"org_domain\": \"democorp.com\", \"contact_email\": \"demo@democorp.com\"}" | python3 -m json.tool'

# Rating — valid
alias pact-rate-valid='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-001\"}" | python3 -m json.tool'

# Rating — anti-gaming (each should return HTTP 403)
alias pact-rate-self='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_freightbot_01\", \"score\": 5, \"transaction_id\": \"txn-demo-002\"}" | python3 -m json.tool'
alias pact-rate-dupe='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-001\"}" | python3 -m json.tool'
alias pact-rate-blocked='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_riskroute_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-003\"}" | python3 -m json.tool'

# Local dev
alias pact-demo='cd ~/Desktop/pact-protocol && python3 demo_agent.py'
alias pact-server='cd ~/Desktop/pact-protocol && python3 -m uvicorn main:app --reload --port 8001'
alias pact-push='git add . && git commit -m "update" && git push'
alias pact-sdk='cd ~/Desktop/pact-protocol && python3 pact_sdk.py'

# ─────────────────────────────────────────────────────────────────────────────
EOF

echo "  [done]"
echo ""

# ── Step 3: Reload shell config so aliases are available immediately ─────────

echo "Reloading $ZSHRC ..."
# shellcheck disable=SC1090
source "$ZSHRC"
echo "  [done]"

# ── Step 4: Confirm the quote pattern is correct ─────────────────────────────
# Grep pact-verify-good out of .zshrc so the caller can see the exact string
# that was written and verify the quoting is valid before using any alias.

echo ""
echo "── Quote check (pact-verify-good as written to $ZSHRC):"
grep "pact-verify-good" "$ZSHRC"

# ── Step 5: Print full alias reference ───────────────────────────────────────

echo ""
echo "PACT — Setup Complete"
echo "══════════════════════════════════════════════"
echo ""
echo "NETWORK"
echo "  pact-wake              Wake up Render server (raw, no formatting)"
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
echo "  pact-rate-valid        Submit a valid rating (freightbot → shipchain)"
echo "  pact-rate-self         Attempt self-rating — blocked (Rule D)"
echo "  pact-rate-dupe         Attempt duplicate transaction — blocked (Rule C)"
echo "  pact-rate-blocked      Low-trust rater attempt — blocked (Rule A)"
echo ""
echo "LOCAL DEV"
echo "  pact-demo              Run demo_agent.py against live server"
echo "  pact-server            Start local API server on port 8001"
echo "  pact-push              git add + commit + push from current directory"
echo "  pact-sdk               Run pact_sdk.py demo"
echo ""
echo "══════════════════════════════════════════════"
echo "PACT is live at $BASE"
echo "Start with: pact-wake → pact-registry → pact-verify-good"
echo "══════════════════════════════════════════════"
echo ""
