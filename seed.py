# seed.py — Populate the PACT database with 10 realistic logistics-vertical agents

import sqlite3
import json
from datetime import datetime, timezone, timedelta
import random

DB_PATH = "pact.db"

# ── Seed data definitions ────────────────────────────────────────────────────

# 7 clean agents: verified, trust_score 55-90, healthy transaction counts
CLEAN_AGENTS = [
    {
        "agent_id":               "agent_freightbot_01",
        "org_name":               "FreightBot Logistics",
        "org_domain":             "freightbot.io",
        "contact_email":          "ops@freightbot.io",
        "verified":               1,
        "trust_score":            88,
        "transaction_count":      183,
        "flags":                  [],
        "endpoint_url":           "https://freightbot.io/api/agent",
        "protocol":               "REST",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "x402",
        "capabilities":           ["freight_booking", "customs_clearance", "shipment_tracking", "carrier_negotiation"],
    },
    {
        "agent_id":               "agent_cargovfy_01",
        "org_name":               "CargoVerify Inc.",
        "org_domain":             "cargoverify.com",
        "contact_email":          "registry@cargoverify.com",
        "verified":               1,
        "trust_score":            82,
        "transaction_count":      140,
        "flags":                  [],
        "endpoint_url":           "https://api.cargoverify.com/v2/agent",
        "protocol":               "REST",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "stripe",
        "capabilities":           ["cargo_verification", "document_validation", "compliance_check", "certificate_issuance"],
    },
    {
        "agent_id":               "agent_shipchain_01",
        "org_name":               "ShipChain Protocol",
        "org_domain":             "shipchain.network",
        "contact_email":          "agent@shipchain.network",
        "verified":               1,
        "trust_score":            76,
        "transaction_count":      97,
        "flags":                  [],
        "endpoint_url":           "https://node.shipchain.network/agent",
        "protocol":               "gRPC",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "x402",
        "capabilities":           ["freight_booking", "shipment_tracking", "port_coordination", "bill_of_lading"],
    },
    {
        "agent_id":               "agent_tradelens_01",
        "org_name":               "TradeLens AI",
        "org_domain":             "tradelens.ai",
        "contact_email":          "bot@tradelens.ai",
        "verified":               1,
        "trust_score":            71,
        "transaction_count":      55,
        "flags":                  [],
        "endpoint_url":           "https://tradelens.ai/graphql",
        "protocol":               "GraphQL",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "stripe",
        "capabilities":           ["trade_finance", "document_validation", "customs_clearance", "compliance_check"],
    },
    {
        "agent_id":               "agent_portex_01",
        "org_name":               "PortEx Automation",
        "org_domain":             "portex.systems",
        "contact_email":          "agent@portex.systems",
        "verified":               1,
        "trust_score":            65,
        "transaction_count":      42,
        "flags":                  [],
        "endpoint_url":           "https://portex.systems/api/v1/agent",
        "protocol":               "REST",
        "accepted_terms_format":  "XML",
        "settlement_rail":        "manual",
        "capabilities":           ["port_coordination", "container_management", "yard_scheduling", "vessel_tracking"],
    },
    {
        "agent_id":               "agent_routeiq_01",
        "org_name":               "RouteIQ Solutions",
        "org_domain":             "routeiq.co",
        "contact_email":          "routing@routeiq.co",
        "verified":               1,
        "trust_score":            59,
        "transaction_count":      28,
        "flags":                  [],
        "endpoint_url":           "https://routeiq.co/agent/endpoint",
        "protocol":               "REST",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "x402",
        "capabilities":           ["route_optimisation", "last_mile_delivery", "schedule_management", "fleet_dispatch"],
    },
    {
        "agent_id":               "agent_supplylink_01",
        "org_name":               "SupplyLink Dynamics",
        "org_domain":             "supplylink.net",
        "contact_email":          "api@supplylink.net",
        "verified":               1,
        "trust_score":            55,
        "transaction_count":      14,
        "flags":                  [],
        "endpoint_url":           "https://supplylink.net/api/agent",
        "protocol":               "gRPC",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "manual",
        "capabilities":           ["supplier_onboarding", "inventory_sync", "purchase_order_management", "demand_forecasting"],
    },
]

# 2 flagged agents: low trust — capabilities are limited or absent due to misconduct
FLAGGED_AGENTS = [
    {
        "agent_id":               "agent_spoofex_99",
        "org_name":               "SpoofEx Logistics",
        "org_domain":             "spoofex.biz",
        "contact_email":          "noreply@spoofex.biz",
        "verified":               1,
        "trust_score":            22,
        "transaction_count":      11,
        "flags":                  ["dispute_history"],
        "endpoint_url":           "https://spoofex.biz/agent",
        "protocol":               "REST",
        "accepted_terms_format":  "JSON",
        "settlement_rail":        "manual",
        "capabilities":           ["freight_booking"],   # stripped down due to dispute history
    },
    {
        "agent_id":               "agent_fakecargo_77",
        "org_name":               "FakeCargo Systems",
        "org_domain":             "fakecargo.org",
        "contact_email":          "ghost@fakecargo.org",
        "verified":               1,
        "trust_score":            8,
        "transaction_count":      3,
        "flags":                  ["fabricated_output"],
        "endpoint_url":           "https://fakecargo.org/api",
        "protocol":               "REST",
        "accepted_terms_format":  "XML",
        "settlement_rail":        "manual",
        "capabilities":           [],   # no verified capabilities — fabricated output flag
    },
]

# 1 unregistered / shadow agent — no routing or capabilities; never properly onboarded
UNREGISTERED_AGENT = [
    {
        "agent_id":               "agent_ghost_00",
        "org_name":               "GhostFreight Unknown",
        "org_domain":             "ghostfreight.unknown",
        "contact_email":          "void@ghostfreight.unknown",
        "verified":               0,
        "trust_score":            0,
        "transaction_count":      0,
        "flags":                  [],
        "endpoint_url":           None,
        "protocol":               None,
        "accepted_terms_format":  None,
        "settlement_rail":        None,
        "capabilities":           [],
    },
]


# ── Insertion logic ──────────────────────────────────────────────────────────

def _now_minus(days: int) -> str:
    """Return an ISO timestamp some days in the past — gives realistic date variety."""
    t = datetime.now(timezone.utc) - timedelta(days=days)
    return t.isoformat()

def seed_database() -> None:
    """Drop existing agent rows and insert fresh seed data into pact.db."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Ensure tables exist (safe if already created by the API)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id               TEXT PRIMARY KEY,
            org_name               TEXT NOT NULL,
            org_domain             TEXT NOT NULL,
            contact_email          TEXT NOT NULL,
            verified               INTEGER NOT NULL DEFAULT 0,
            trust_score            INTEGER NOT NULL DEFAULT 40,
            transaction_count      INTEGER NOT NULL DEFAULT 0,
            flags                  TEXT    NOT NULL DEFAULT '[]',
            registered_at          TEXT    NOT NULL,
            last_active            TEXT    NOT NULL,
            endpoint_url           TEXT,
            protocol               TEXT,
            accepted_terms_format  TEXT,
            settlement_rail        TEXT,
            capabilities           TEXT    NOT NULL DEFAULT '[]'
        )
    """)
    # Migrate existing databases that predate the routing/capability columns
    for col, col_type in [
        ("endpoint_url",          "TEXT"),
        ("protocol",              "TEXT"),
        ("accepted_terms_format", "TEXT"),
        ("settlement_rail",       "TEXT"),
        ("capabilities",          "TEXT NOT NULL DEFAULT '[]'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE agents ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # column already present
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            rater_agent_id  TEXT NOT NULL REFERENCES agents(agent_id),
            rated_agent_id  TEXT NOT NULL REFERENCES agents(agent_id),
            score           INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
            transaction_id  TEXT NOT NULL UNIQUE,
            created_at      TEXT NOT NULL
        )
    """)

    all_agents = CLEAN_AGENTS + FLAGGED_AGENTS + UNREGISTERED_AGENT

    inserted = 0
    skipped  = 0

    for i, a in enumerate(all_agents):
        try:
            conn.execute(
                """
                INSERT INTO agents
                    (agent_id, org_name, org_domain, contact_email,
                     verified, trust_score, transaction_count, flags,
                     registered_at, last_active,
                     endpoint_url, protocol, accepted_terms_format, settlement_rail,
                     capabilities)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a["agent_id"],
                    a["org_name"],
                    a["org_domain"],
                    a["contact_email"],
                    a["verified"],
                    a["trust_score"],
                    a["transaction_count"],
                    json.dumps(a["flags"]),
                    _now_minus(180 - i * 10),        # stagger registration dates
                    _now_minus(i * 2),                # stagger last_active dates
                    a.get("endpoint_url"),
                    a.get("protocol"),
                    a.get("accepted_terms_format"),
                    a.get("settlement_rail"),
                    json.dumps(a.get("capabilities", [])),
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # Agent already exists — backfill routing and capability columns if still NULL/empty
            conn.execute(
                """
                UPDATE agents
                   SET endpoint_url          = COALESCE(endpoint_url,          ?),
                       protocol              = COALESCE(protocol,              ?),
                       accepted_terms_format = COALESCE(accepted_terms_format, ?),
                       settlement_rail       = COALESCE(settlement_rail,       ?),
                       capabilities          = CASE
                                                 WHEN capabilities IS NULL OR capabilities = '[]'
                                                 THEN ? ELSE capabilities
                                               END
                 WHERE agent_id = ?
                """,
                (
                    a.get("endpoint_url"),
                    a.get("protocol"),
                    a.get("accepted_terms_format"),
                    a.get("settlement_rail"),
                    json.dumps(a.get("capabilities", [])),
                    a["agent_id"],
                ),
            )
            print(f"  [updated routing+capabilities] {a['agent_id']}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\nSeed complete: {inserted} agents inserted, {skipped} skipped.")
    print("Run 'python main.py' or 'uvicorn main:app --reload' to start the API.\n")

    # Pretty-print a summary table
    print(f"{'Agent ID':<30} {'Org':<25} {'Score':>5} {'Verified':>8} {'Flags'}")
    print("-" * 80)
    for a in all_agents:
        flags_str = ", ".join(a["flags"]) if a["flags"] else "—"
        verified_str = "yes" if a["verified"] else "no"
        print(f"{a['agent_id']:<30} {a['org_name']:<25} {a['trust_score']:>5} {verified_str:>8}  {flags_str}")


if __name__ == "__main__":
    seed_database()
