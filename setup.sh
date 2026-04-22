#!/usr/bin/env bash
# setup.sh — One-command installer for Aidress demo aliases on macOS
#
# Writes curl shortcuts for every Aidress endpoint into ~/.zshrc.
#
# Idempotent: strips all existing pact- and aidress- lines before re-writing,
# so running the script twice produces a clean, duplicate-free result.
#
# Quoting strategy:
#   Every alias uses single quotes as the outer delimiter.
#   JSON bodies use escaped double quotes inside: -d "{\"key\": \"val\"}"
#
# Usage:
#   bash setup.sh

set -euo pipefail

ZSHRC="$HOME/.zshrc"
BASE="https://api.aidress.ai"

echo ""
echo "Aidress — Installer"
echo "══════════════════════════════════════════════"
echo ""

# ── Step 1: Remove any existing pact- and aidress- aliases ──────────────────
# Deletes every line containing "pact-" or "aidress-" so re-runs don't
# accumulate duplicates.

echo "Removing existing pact- and aidress- aliases from $ZSHRC ..."
sed -i '' '/pact-/d' "$ZSHRC"
sed -i '' '/aidress-/d' "$ZSHRC"
echo "  [done]"
echo ""

# ── Step 2: Append all aliases via a quoted-delimiter heredoc ───────────────
# <<'EOF' treats the body as a completely literal string — no variable
# expansion, no quote interpretation by bash.

echo "Writing aliases to $ZSHRC ..."

cat >> "$ZSHRC" << 'EOF'

# ── Aidress aliases ──────────────────────────────────────────────────────────

# Wake + Network
alias aidress-wake='curl -s https://api.aidress.ai/registry'
alias aidress-registry='curl -s https://api.aidress.ai/registry | python3 -m json.tool'

# Verify
alias aidress-verify-good='curl -s -X POST https://api.aidress.ai/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"agent_freightbot_01\"}" | python3 -m json.tool'
alias aidress-verify-flagged='curl -s -X POST https://api.aidress.ai/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"agent_riskroute_01\"}" | python3 -m json.tool'
alias aidress-verify-unknown='curl -s -X POST https://api.aidress.ai/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"unknown-agent-999\"}" | python3 -m json.tool'
alias aidress-verify-registered='curl -s -X POST https://api.aidress.ai/verify -H "Content-Type: application/json" -d "{\"agent_id\": \"demo-agent-001\"}" | python3 -m json.tool'

# Agent Profile
alias aidress-agent-freightbot='curl -s https://api.aidress.ai/agent/agent_freightbot_01 | python3 -m json.tool'
alias aidress-agent-shipchain='curl -s https://api.aidress.ai/agent/agent_shipchain_01 | python3 -m json.tool'
alias aidress-agent-cargovfy='curl -s https://api.aidress.ai/agent/agent_cargovfy_01 | python3 -m json.tool'

# Discovery
alias aidress-match-freight='curl -s -X POST https://api.aidress.ai/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"freight_booking\", \"customs_clearance\"]}" | python3 -m json.tool'
alias aidress-match-routing='curl -s -X POST https://api.aidress.ai/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"route_optimisation\", \"last_mile_delivery\"]}" | python3 -m json.tool'
alias aidress-match-customs='curl -s -X POST https://api.aidress.ai/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"customs_clearance\", \"compliance_check\"]}" | python3 -m json.tool'
alias aidress-match-fuzzy='curl -s -X POST https://api.aidress.ai/match -H "Content-Type: application/json" -d "{\"required_capabilities\": [\"freight\"]}" | python3 -m json.tool'

# Register
alias aidress-register='curl -s -X POST https://api.aidress.ai/register -H "Content-Type: application/json" -d "{\"agent_id\": \"demo-agent-001\", \"org_name\": \"Demo Corp\", \"org_domain\": \"democorp.com\", \"contact_email\": \"demo@democorp.com\"}" | python3 -m json.tool'

# Rating — valid
alias aidress-rate-valid='curl -s -X POST https://api.aidress.ai/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-001\"}" | python3 -m json.tool'

# Rating — anti-gaming (each returns HTTP 403)
alias aidress-rate-self='curl -s -X POST https://api.aidress.ai/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_freightbot_01\", \"score\": 5, \"transaction_id\": \"txn-demo-002\"}" | python3 -m json.tool'
alias aidress-rate-dupe='curl -s -X POST https://api.aidress.ai/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_freightbot_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-001\"}" | python3 -m json.tool'
alias aidress-rate-blocked='curl -s -X POST https://api.aidress.ai/rate -H "Content-Type: application/json" -d "{\"rater_agent_id\": \"agent_riskroute_01\", \"rated_agent_id\": \"agent_shipchain_01\", \"score\": 5, \"transaction_id\": \"txn-demo-003\"}" | python3 -m json.tool'

# Local dev
alias aidress-demo='cd ~/Desktop/aidress && python3 demo_agent.py'
alias aidress-server='cd ~/Desktop/aidress && python3 -m uvicorn main:app --reload --port 8001'
alias aidress-push='git add . && git commit -m "update" && git push'
alias aidress-sdk='cd ~/Desktop/aidress && python3 aidress_sdk.py'

# ─────────────────────────────────────────────────────────────────────────────
EOF

echo "  [done]"
echo ""

# ── Step 3: Reload shell config ─────────────────────────────────────────────

echo "Reloading $ZSHRC ..."
# shellcheck disable=SC1090
source "$ZSHRC"
echo "  [done]"

# ── Step 4: Confirmation table ──────────────────────────────────────────────

echo ""
echo "Aidress — Setup Complete"
echo "══════════════════════════════════════════════"
echo ""
echo "NETWORK"
echo "  aidress-wake              Wake up server (raw, no formatting)"
echo "  aidress-registry          See all trusted agents on the network"
echo ""
echo "VERIFY"
echo "  aidress-verify-good       Verify trusted agent (FreightBot, score 88)"
echo "  aidress-verify-flagged    Verify flagged agent (low score, blocked)"
echo "  aidress-verify-unknown    Verify unknown agent (not on network)"
echo "  aidress-verify-registered Verify agent you just registered"
echo ""
echo "DISCOVER"
echo "  aidress-match-freight     Find agents for freight + customs"
echo "  aidress-match-routing     Find agents for routing + last mile"
echo "  aidress-match-customs     Find agents for customs + compliance"
echo "  aidress-match-fuzzy       Fuzzy match — \"freight\" resolves to freight_booking"
echo ""
echo "AGENT PROFILE"
echo "  aidress-agent-freightbot  Full profile — FreightBot Logistics"
echo "  aidress-agent-shipchain   Full profile — ShipChain Protocol"
echo "  aidress-agent-cargovfy    Full profile — CargoVerify Inc"
echo ""
echo "REGISTER"
echo "  aidress-register          Register a new agent on the network"
echo ""
echo "RATING"
echo "  aidress-rate-valid        Submit a valid rating (freightbot → shipchain)"
echo "  aidress-rate-self         Attempt self-rating — blocked (Rule D)"
echo "  aidress-rate-dupe         Attempt duplicate transaction — blocked (Rule C)"
echo "  aidress-rate-blocked      Low-trust rater attempt — blocked (Rule A)"
echo ""
echo "LOCAL DEV"
echo "  aidress-demo              Run demo_agent.py against live server"
echo "  aidress-server            Start local API server on port 8001"
echo "  aidress-push              git add + commit + push"
echo "  aidress-sdk               Run aidress_sdk.py demo"
echo ""
echo "══════════════════════════════════════════════"
echo "Aidress is live at https://api.aidress.ai"
echo "Start with: aidress-wake → aidress-registry → aidress-verify-good"
echo "══════════════════════════════════════════════"
echo ""
