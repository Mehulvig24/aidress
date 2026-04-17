#!/usr/bin/env bash
# setup.sh — One-command installer for PACT demo aliases on macOS
#
# Writes curl shortcuts for every PACT endpoint into ~/.zshrc.
#
# Idempotent: strips all existing pact- lines before re-writing, so running
# the script twice produces a clean, duplicate-free result.
#
# Quoting strategy:
#   Every alias uses single quotes as the outer delimiter. JSON bodies are
#   embedded using the '\'' technique — end the single-quoted string, insert
#   a literal ' via backslash-escape, then open a new single-quoted string.
#   This means the JSON needs zero escaping and is passed to curl verbatim.
#
#   Pattern:  alias name='curl ... -d '\''{"key": "val"}'\'' | python3 ...'
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
# <<'EOF' treats the body as a completely literal string — no variable
# expansion, no quote interpretation by bash. The '\'' sequences are written
# verbatim and interpreted by zsh when it sources ~/.zshrc.

echo "Writing aliases to $ZSHRC ..."

cat >> "$ZSHRC" << 'EOF'

# ── PACT aliases ─────────────────────────────────────────────────────────────

# Wake + Network
alias pact-wake='curl -s https://pact-protocol.onrender.com/registry'
alias pact-registry='curl -s https://pact-protocol.onrender.com/registry | python3 -m json.tool'

# Verify
alias pact-verify-good='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d '\''{"agent_id": "agent_freightbot_01"}'\'' | python3 -m json.tool'
alias pact-verify-flagged='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d '\''{"agent_id": "agent_riskroute_01"}'\'' | python3 -m json.tool'
alias pact-verify-unknown='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d '\''{"agent_id": "unknown-agent-999"}'\'' | python3 -m json.tool'
alias pact-verify-registered='curl -s -X POST https://pact-protocol.onrender.com/verify -H "Content-Type: application/json" -d '\''{"agent_id": "demo-agent-001"}'\'' | python3 -m json.tool'

# Agent Profile
alias pact-agent-freightbot='curl -s https://pact-protocol.onrender.com/agent/agent_freightbot_01 | python3 -m json.tool'
alias pact-agent-shipchain='curl -s https://pact-protocol.onrender.com/agent/agent_shipchain_01 | python3 -m json.tool'
alias pact-agent-cargovfy='curl -s https://pact-protocol.onrender.com/agent/agent_cargovfy_01 | python3 -m json.tool'

# Discovery
alias pact-match-freight='curl -s -X POST https://pact-protocol.onrender.com/match -H "Content-Type: application/json" -d '\''{"required_capabilities": ["freight_booking", "customs_clearance"]}'\'' | python3 -m json.tool'
alias pact-match-routing='curl -s -X POST https://pact-protocol.onrender.com/match -H "Content-Type: application/json" -d '\''{"required_capabilities": ["route_optimisation", "last_mile_delivery"]}'\'' | python3 -m json.tool'
alias pact-match-customs='curl -s -X POST https://pact-protocol.onrender.com/match -H "Content-Type: application/json" -d '\''{"required_capabilities": ["customs_clearance", "compliance_check"]}'\'' | python3 -m json.tool'

# Register
alias pact-register='curl -s -X POST https://pact-protocol.onrender.com/register -H "Content-Type: application/json" -d '\''{"agent_id": "demo-agent-001", "org_name": "Demo Corp", "org_domain": "democorp.com", "contact_email": "demo@democorp.com"}'\'' | python3 -m json.tool'

# Rating — valid
alias pact-rate-valid='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d '\''{"rater_agent_id": "agent_freightbot_01", "rated_agent_id": "agent_shipchain_01", "score": 5, "transaction_id": "txn-demo-001"}'\'' | python3 -m json.tool'

# Rating — anti-gaming (each returns HTTP 403)
alias pact-rate-self='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d '\''{"rater_agent_id": "agent_freightbot_01", "rated_agent_id": "agent_freightbot_01", "score": 5, "transaction_id": "txn-demo-002"}'\'' | python3 -m json.tool'
alias pact-rate-dupe='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d '\''{"rater_agent_id": "agent_freightbot_01", "rated_agent_id": "agent_shipchain_01", "score": 5, "transaction_id": "txn-demo-001"}'\'' | python3 -m json.tool'
alias pact-rate-blocked='curl -s -X POST https://pact-protocol.onrender.com/rate -H "Content-Type: application/json" -d '\''{"rater_agent_id": "agent_riskroute_01", "rated_agent_id": "agent_shipchain_01", "score": 5, "transaction_id": "txn-demo-003"}'\'' | python3 -m json.tool'

# Local dev
alias pact-demo='cd ~/Desktop/pact-protocol && python3 demo_agent.py'
alias pact-server='cd ~/Desktop/pact-protocol && python3 -m uvicorn main:app --reload --port 8001'
alias pact-push='git add . && git commit -m "update" && git push'
alias pact-sdk='cd ~/Desktop/pact-protocol && python3 pact_sdk.py'

# ─────────────────────────────────────────────────────────────────────────────
EOF

echo "  [done]"
echo ""

# ── Step 3: Reload shell config ──────────────────────────────────────────────

echo "Reloading $ZSHRC ..."
# shellcheck disable=SC1090
source "$ZSHRC"
echo "  [done]"

# ── Step 4: Quote check ───────────────────────────────────────────────────────
# Print pact-verify-good exactly as written to ~/.zshrc so you can confirm
# the '\'' quoting pattern is intact before running any alias.

echo ""
echo "── Quote check (pact-verify-good as written to $ZSHRC):"
grep "pact-verify-good" "$ZSHRC"

# ── Step 5: Confirmation table ───────────────────────────────────────────────

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
