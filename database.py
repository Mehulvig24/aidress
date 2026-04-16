# database.py — SQLite setup and every database operation used by the API

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "pact.db"


# ── Connection helper ────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite file and return rows as dict-like objects."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema creation ──────────────────────────────────────────────────────────

def create_tables() -> None:
    """Create the agents and ratings tables if they don't already exist."""
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id               TEXT PRIMARY KEY,
                org_name               TEXT NOT NULL,
                org_domain             TEXT NOT NULL,
                contact_email          TEXT NOT NULL,
                verified               INTEGER NOT NULL DEFAULT 0,   -- 0 = false, 1 = true
                trust_score            INTEGER NOT NULL DEFAULT 40,
                transaction_count      INTEGER NOT NULL DEFAULT 0,
                flags                  TEXT    NOT NULL DEFAULT '[]', -- JSON array
                registered_at          TEXT    NOT NULL,
                last_active            TEXT    NOT NULL,
                endpoint_url           TEXT,   -- the agent's reachable API address
                protocol               TEXT,   -- REST | GraphQL | gRPC
                accepted_terms_format  TEXT,   -- JSON | XML
                settlement_rail        TEXT    -- x402 | stripe | manual
            )
        """)

        # ── Live migration for databases created before routing columns existed ──
        # SQLite does not support ADD COLUMN IF NOT EXISTS, so we attempt each
        # ALTER and silently ignore the error if the column is already there.
        _add_column_if_missing(conn, "agents", "endpoint_url",          "TEXT")
        _add_column_if_missing(conn, "agents", "protocol",              "TEXT")
        _add_column_if_missing(conn, "agents", "accepted_terms_format", "TEXT")
        _add_column_if_missing(conn, "agents", "settlement_rail",       "TEXT")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                rater_agent_id  TEXT NOT NULL REFERENCES agents(agent_id),
                rated_agent_id  TEXT NOT NULL REFERENCES agents(agent_id),
                score           INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
                transaction_id  TEXT NOT NULL UNIQUE,   -- one rating per transaction
                created_at      TEXT NOT NULL
            )
        """)
    conn.close()


# ── Agent operations ─────────────────────────────────────────────────────────

def get_agent(agent_id: str) -> Optional[dict]:
    """Fetch a single agent row by its ID, or return None if not found."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_agent_dict(row)


def agent_domain_exists(org_domain: str) -> bool:
    """Return True if any registered agent already uses this org_domain."""
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM agents WHERE org_domain = ?", (org_domain,)
    ).fetchone()
    conn.close()
    return row is not None


def create_agent(
    agent_id: str,
    org_name: str,
    org_domain: str,
    contact_email: str,
) -> dict:
    """Insert a new agent with default trust values and return the created record."""
    now = _now()
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO agents
                (agent_id, org_name, org_domain, contact_email,
                 verified, trust_score, transaction_count, flags,
                 registered_at, last_active)
            VALUES (?, ?, ?, ?, 0, 40, 0, '[]', ?, ?)
            """,
            (agent_id, org_name, org_domain, contact_email, now, now),
        )
    conn.close()
    return get_agent(agent_id)


def get_all_verified_agents() -> list[dict]:
    """Return every agent that is verified AND has a trust_score of 50 or above."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM agents WHERE verified = 1 AND trust_score >= 50"
    ).fetchall()
    conn.close()
    return [_row_to_agent_dict(r) for r in rows]


def update_agent_trust_score(agent_id: str, new_score: int) -> None:
    """Overwrite the trust_score field for a given agent."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE agents SET trust_score = ?, last_active = ? WHERE agent_id = ?",
            (new_score, _now(), agent_id),
        )
    conn.close()


# ── Rating operations ────────────────────────────────────────────────────────

def transaction_id_exists(transaction_id: str) -> bool:
    """Return True if this transaction_id has already been used for a rating."""
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM ratings WHERE transaction_id = ?", (transaction_id,)
    ).fetchone()
    conn.close()
    return row is not None


def create_rating(
    rater_agent_id: str,
    rated_agent_id: str,
    score: int,
    transaction_id: str,
) -> None:
    """Insert a new rating record into the database."""
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO ratings
                (rater_agent_id, rated_agent_id, score, transaction_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rater_agent_id, rated_agent_id, score, transaction_id, _now()),
        )
    conn.close()


def get_ratings_for_agent(rated_agent_id: str) -> list[dict]:
    """Return all rating rows where this agent was the one being rated."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ratings WHERE rated_agent_id = ? ORDER BY created_at DESC",
        (rated_agent_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ratings_with_rater_domain(rated_agent_id: str) -> list[dict]:
    """Return ratings joined with the rater's org_domain — needed for the 20% cap check."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT r.score, a.org_domain AS rater_domain
          FROM ratings r
          JOIN agents  a ON a.agent_id = r.rater_agent_id
         WHERE r.rated_agent_id = ?
        """,
        (rated_agent_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Trust score calculation ──────────────────────────────────────────────────

def compute_new_trust_score(rated_agent_id: str, new_score: int, rater_domain: str) -> int:
    """
    Recalculate trust_score for rated_agent after a new rating is added.

    Rules:
      1. Base score is the average of all received ratings, scaled 1-5 → 0-100.
      2. No single org_domain may contribute more than 20% of the total rating weight.
         If an org exceeds the cap its excess ratings are down-weighted so its total
         contribution is exactly 20%.
    """
    # Fetch all existing ratings (the new one is already saved to DB at this point)
    rows = get_ratings_with_rater_domain(rated_agent_id)

    if not rows:
        return 40  # fallback — should not happen in practice

    total_ratings = len(rows)

    # Count how many ratings came from each domain
    domain_counts: dict[str, int] = {}
    domain_scores: dict[str, list[int]] = {}
    for r in rows:
        d = r["rater_domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
        domain_scores.setdefault(d, []).append(r["score"])

    # The 20% cap: no domain may contribute more than 20% of total weight
    max_weight_per_domain = max(1, int(total_ratings * 0.20))

    weighted_sum   = 0.0
    effective_count = 0

    for domain, scores in domain_scores.items():
        # Clamp how many ratings from this domain we count
        allowed = min(len(scores), max_weight_per_domain)
        # Use the most recent `allowed` ratings (list is already ordered newest-first)
        for s in scores[:allowed]:
            weighted_sum   += s
            effective_count += 1

    if effective_count == 0:
        return 40

    avg_1_to_5 = weighted_sum / effective_count
    # Scale: score of 1 → 0, score of 5 → 100
    scaled = round((avg_1_to_5 - 1) / 4 * 100)
    return max(0, min(100, scaled))


# ── Internal helpers ─────────────────────────────────────────────────────────

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    """Add a column to a table only if it doesn't already exist — safe to call repeatedly."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # column already present — nothing to do


def _row_to_agent_dict(row: sqlite3.Row) -> dict:
    """Convert a raw SQLite row into a plain Python dict with flags parsed and routing nested."""
    d = dict(row)
    d["flags"]    = json.loads(d["flags"])
    d["verified"] = bool(d["verified"])

    # Pull the four routing columns out of the flat row and bundle them into
    # a nested dict so TrustObject can deserialise them as a RoutingBlock.
    routing = {
        "endpoint_url":          d.pop("endpoint_url",          None),
        "protocol":              d.pop("protocol",              None),
        "accepted_terms_format": d.pop("accepted_terms_format", None),
        "settlement_rail":       d.pop("settlement_rail",       None),
    }
    # Only attach the block when at least one field is populated
    if any(v is not None for v in routing.values()):
        d["routing"] = routing

    return d
