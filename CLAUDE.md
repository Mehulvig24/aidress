# Aidress — Claude Code Session Context

## What is Aidress
AI Discovery, Reputation, Exchange & Settlement System. A SWIFT-like coordination network for autonomous AI agents. Allows agents to verify unknown counterparts before transacting. Built by Mehul Vig and Kabir Sadani. Pre-product, resource-constrained, no full-time engineers.

## The Problem
AI agents cannot transact autonomously with unknown counterparts. No universal identity layer, discovery mechanism, or trust standard exists. Validated across 23 runs on 8 tools — zero autonomous completions.

## The Five Layers
Identity, Capability, Terms, Trust, Routing/Settlement. Currently built: Trust, Capability, Routing.

## Live URL
https://aidress.onrender.com

## File Structure
- main.py — FastAPI app, all endpoints
- database.py — SQLite setup, all DB operations
- models.py — Pydantic request/response models
- seed.py — populates DB with 10 logistics agents
- taxonomy.py — capability taxonomy, synonym map, and fuzzy resolution helper
- aidress_sdk.py — one-line Python SDK
- demo_agent.py — simulates agent calling Aidress, shows proceed/caution/abort
- test_ratings.py — tests anti-gaming rating rules
- index.html — visual demo UI
- requirements.txt — dependencies
- Procfile — Render deployment config

## Endpoints
- POST /verify — verify agent, returns trust + capabilities + routing
- POST /register — register new agent, starts at score 40
- POST /rate — rate agent after transaction, anti-gaming enforced
- POST /match — find agents by capability, returns ranked list
- GET /agent/{agent_id} — full agent profile
- GET /registry — all verified agents score >= 50

## Trust Score Tiers
- 0 — unregistered, blocked
- 40 — org verified, pending review
- 50-69 — caution, proceed with limits
- 70-100 — proceed, trusted

## Anti-Gaming Rules
- Rater trust_score >= 50 required
- Same org domain blocked (collusion prevention)
- One rating per transaction_id
- Cannot rate yourself
- Single org capped at 20% of any agent's total score

## Seed Data
10 logistics agents. 7 clean (55-90), 2 flagged (sub-30), 1 unregistered.
Key agents: agent_freightbot_01 (88), agent_cargovfy_01 (100), agent_shipchain_01 (76)

## Coding Rules — follow every session
1. Before editing any file, read it first
2. Before writing any code, state what you are changing and why
3. Removing or refactoring code is fine — state what is being removed, why, and confirm no existing endpoint or test is broken before proceeding
4. If a change touches more than 3 files, pause and confirm with the user before proceeding
5. Add precise technical comments on every function — engineer-level, not simplified
6. Follow this order when adding new endpoints: models.py → database.py → main.py
7. Prefer small focused changes over large rewrites
8. SQLite only — no external DB dependencies until explicitly told to migrate
9. All endpoints return consistent JSON shapes defined in models.py

## Testing Rules — mandatory before marking anything done
1. Test every endpoint change with curl against localhost
2. Test every database change with a direct SQLite query
3. Run python3 aidress_sdk.py after any SDK change
4. Run python3 demo_agent.py after any change to core verify/match logic
5. Run python3 test_ratings.py after any change to rating logic
6. NEVER mark a task complete without pasting actual test output
7. If a test fails, fix it before moving on — do not skip

## Token Efficiency Rules
1. Do not re-read files already read in this session unless asked
2. Do not repeat large code blocks — summarise what changed instead
3. Show only relevant fields in test output, not full JSON, unless asked
4. Plan before coding — state the approach before writing anything
5. If a task is ambiguous, ask one clarifying question before starting — not mid-task
6. Batch related changes into single operations where possible

## Current Status
All phases complete and live on Render. Next priorities:
1. JavaScript SDK
2. Supabase migration (trigger: first real design partner)
3. Terms layer
4. Properly hosted UI

## Target Users
Developers building agents on Replit, Cursor, Lovable. First vertical: logistics. Wedge: trust verification as standalone API. First design partner recruitment via developer communities describing the exact failure Aidress solves.

## Architecture Notes
- Google A2A is complementary not competitive — A2A handles agent messaging, Aidress handles the coordination stack above it
- SWIFT analogy is central to positioning
- Do not over-engineer — one working design partner beats full protocol design
- Supabase migration path: swap SQLite connection in database.py for asyncpg/psycopg2, update Render environment variables, run schema migration — everything else stays identical
