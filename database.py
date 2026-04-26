# database.py — SQLite setup and every database operation used by the API

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "aidress.db"


# ── Connection helper ────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite file and return rows as dict-like objects."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
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
                settlement_rail        TEXT,   -- x402 | stripe | manual
                capabilities           TEXT    NOT NULL DEFAULT '[]'  -- JSON array of capability strings
            )
        """)

        # ── Live migration for databases created before routing/capability columns existed ──
        # SQLite does not support ADD COLUMN IF NOT EXISTS, so we attempt each
        # ALTER and silently ignore the error if the column is already there.
        _add_column_if_missing(conn, "agents", "endpoint_url",          "TEXT")
        _add_column_if_missing(conn, "agents", "protocol",              "TEXT")
        _add_column_if_missing(conn, "agents", "accepted_terms_format", "TEXT")
        _add_column_if_missing(conn, "agents", "settlement_rail",       "TEXT")
        _add_column_if_missing(conn, "agents", "capabilities",          "TEXT NOT NULL DEFAULT '[]'")
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
    capabilities:          list  = None,
    endpoint_url:          str   = None,
    protocol:              str   = None,
    accepted_terms_format: str   = None,
    settlement_rail:       str   = None,
) -> dict:
    """Insert a new agent with default trust values and return the created record.

    Routing and capability fields are optional — agents can supply them at
    registration time or have them added later via admin tooling.
    """
    now = _now()
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO agents
                (agent_id, org_name, org_domain, contact_email,
                 verified, trust_score, transaction_count, flags,
                 registered_at, last_active,
                 capabilities, endpoint_url, protocol,
                 accepted_terms_format, settlement_rail)
            VALUES (?, ?, ?, ?, 0, 40, 0, '[]', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id, org_name, org_domain, contact_email, now, now,
                json.dumps(capabilities or []),
                endpoint_url, protocol, accepted_terms_format, settlement_rail,
            ),
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


def get_agents_with_capabilities(required: list[str]) -> list[dict]:
    """
    Return verified agents (trust_score >= 50) whose capabilities overlap with
    the required list, ranked by match_score desc then trust_score desc.

    Fuzzy matching pipeline:
      1. Each input string is normalised via taxonomy.normalize_capability()
         (synonym lookup → canonical check → substring match).
      2. The union of all resolved tags forms the target set.
      3. Each candidate agent is scored by how many target tags it has.
      4. Agents with at least one match are returned; zero-match agents excluded.
    """
    from taxonomy import normalize_capability

    candidates = get_all_verified_agents()

    # Resolve every input term to canonical tags (one term may resolve to many)
    resolved_tags: set[str] = set()
    for cap in required:
        resolved_tags.update(normalize_capability(cap))

    if not resolved_tags:
        return []

    results = []
    for agent in candidates:
        agent_caps = set(agent.get("capabilities", []))
        matched = resolved_tags & agent_caps
        if matched:
            agent["match_score"] = len(matched)
            results.append(agent)

    # Best coverage first, then highest trust as tiebreaker
    results.sort(key=lambda a: (a["match_score"], a["trust_score"]), reverse=True)
    return results


def set_agent_verified(agent_id: str) -> None:
    """Mark an agent as verified (verified = 1) and update last_active timestamp."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE agents SET verified = 1, last_active = ? WHERE agent_id = ?",
            (_now(), agent_id),
        )
    conn.close()


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
    """Convert a raw SQLite row into a plain Python dict with flags/capabilities parsed and routing nested."""
    d = dict(row)
    d["flags"]        = json.loads(d["flags"])
    d["capabilities"] = json.loads(d.get("capabilities") or "[]")
    d["verified"]     = bool(d["verified"])

    raw_routing = d.get("routing")
    d["routing"] = json.loads(raw_routing) if raw_routing else None

    return d
