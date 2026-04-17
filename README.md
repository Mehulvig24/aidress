# PACT — Protocol for Autonomous Coordination and Trust

A trust and identity registry for autonomous AI agents, modelled after how SWIFT works for banks.

When **Agent A** is about to transact with **Agent B** it has never met, it calls PACT's `/verify` endpoint. PACT looks up Agent B and returns a **TrustObject** — a verified score, flags, and identity metadata — so Agent A can decide whether to proceed.

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Seed the database

Populates `pact.db` with 10 realistic logistics-vertical agents (7 clean, 2 flagged, 1 unregistered):

```bash
python seed.py
```

### 3. Start the API server

```bash
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**.

Interactive docs (Swagger UI): **http://localhost:8000/docs**

---

## Endpoints

### `POST /verify` — Look up an agent before transacting

```bash
curl -s -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_freightbot_01"}' | python -m json.tool
```

Unknown agent (not in registry):
```bash
curl -s -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "some_unknown_agent"}' | python -m json.tool
```

---

### `POST /register` — Onboard a new agent

```bash
curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id":      "agent_newco_01",
    "org_name":      "NewCo Logistics",
    "org_domain":    "newco-logistics.com",
    "contact_email": "agent@newco-logistics.com"
  }' | python -m json.tool
```

Returns `201 Created` with `status: "pending_review"` and a starting `trust_score` of 40.  
Returns `409 Conflict` if the `agent_id` or `org_domain` is already taken.

---

### `POST /rate` — Submit a trust rating after a transaction

```bash
curl -s -X POST http://localhost:8000/rate \
  -H "Content-Type: application/json" \
  -d '{
    "rater_agent_id": "agent_freightbot_01",
    "rated_agent_id": "agent_newco_01",
    "score":           4,
    "transaction_id":  "txn_abc_001"
  }' | python -m json.tool
```

**Anti-gaming rules enforced (returns `403` if violated):**
| Rule | Description |
|------|-------------|
| A | Rater must have `trust_score >= 50` |
| B | Rater and rated cannot share the same `org_domain` (collusion block) |
| C | Each `transaction_id` can only be used once |
| D | An agent cannot rate itself |

The rated agent's `trust_score` is recalculated as a weighted average of all received ratings (1–5 → 0–100 scale), with no single org contributing more than 20% of the total weight.

---

### `GET /agent/{agent_id}` — Full agent profile

```bash
curl -s http://localhost:8000/agent/agent_freightbot_01 | python -m json.tool
```

Returns the complete record including all ratings received.

---

### `GET /registry` — Public trusted-agent discovery

```bash
curl -s http://localhost:8000/registry | python -m json.tool
```

Returns all agents where `verified = true` AND `trust_score >= 50`.

---

### `POST /match` — Find agents by required capabilities

```bash
curl -s -X POST http://localhost:8000/match \
  -H "Content-Type: application/json" \
  -d '{"required_capabilities": ["freight_booking", "customs_clearance"]}' | python -m json.tool
```

Returns verified agents (trust_score ≥ 50) that have **all** the required capabilities, ranked by trust_score descending. Returns an empty list if nothing matches.

---

## Seed agents reference

| Agent ID | Org | Score | Flags |
|---|---|---|---|
| `agent_freightbot_01` | FreightBot Logistics | 88 | — |
| `agent_cargovfy_01` | CargoVerify Inc. | 82 | — |
| `agent_shipchain_01` | ShipChain Protocol | 76 | — |
| `agent_tradelens_01` | TradeLens AI | 71 | — |
| `agent_portex_01` | PortEx Automation | 65 | — |
| `agent_routeiq_01` | RouteIQ Solutions | 59 | — |
| `agent_supplylink_01` | SupplyLink Dynamics | 55 | — |
| `agent_spoofex_99` | SpoofEx Logistics | 22 | `dispute_history` |
| `agent_fakecargo_77` | FakeCargo Systems | 8 | `fabricated_output` |
| `agent_ghost_00` | GhostFreight Unknown | 0 | *(unverified)* |

---

## Project structure

```
pact-protocol/
  main.py          # FastAPI app — all six endpoints
  database.py      # SQLite setup and every DB operation
  models.py        # Pydantic request/response schemas
  seed.py          # Seed script for the logistics test dataset
  pact_sdk.py      # Standalone Python SDK (no external dependencies)
  demo_agent.py    # Simulates an agent using PACT to vet counterparts
  test_ratings.py  # Integration tests for the POST /rate anti-gaming rules
  index.html       # Single-file demo UI
  Procfile         # Render deployment config
  requirements.txt # Python dependencies (unpinned — pin before production)
  README.md        # This file
  pact.db          # SQLite database (auto-created on first run, gitignored)
```

---

## Trust score algorithm

Ratings are submitted on a 1–5 scale and converted to a 0–100 trust score:

```
scaled_score = (average_rating - 1) / 4 × 100
```

**Collusion cap:** No single `org_domain` may contribute more than 20% of the total rating weight. Excess ratings from any one org are down-weighted automatically so the effective contribution is capped at exactly 20%.
