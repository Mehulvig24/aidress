# main.py — PACT Protocol API: all five endpoints wired up with FastAPI

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import database as db
from models import (
    VerifyRequest,
    RegisterRequest,
    RateRequest,
    MatchRequest,
    AdminVerifyRequest,
    TrustObject,
    RegisterResponse,
    AgentProfile,
    RatingRecord,
)

# ── App lifecycle ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup so the API is self-bootstrapping."""
    db.create_tables()
    yield

app = FastAPI(
    title="Aidress — AI Discovery, Reputation, Exchange & Settlement System",
    description=(
        "A trust and identity registry for autonomous AI agents. "
        "Agents call /verify before transacting with an unknown counterpart."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow any origin so browsers can call the API directly from index.html
# (or any other front-end, including file:// URLs and third-party domains).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 1. POST /verify ──────────────────────────────────────────────────────────

@app.post("/verify", response_model=TrustObject, summary="Look up an agent's trust status")
def verify_agent(body: VerifyRequest):
    """
    Check whether an agent is registered and trustworthy.
    Returns a full TrustObject — including the routing block (endpoint, protocol,
    settlement rail) — or a minimal unregistered response if the agent is not found.
    """
    agent = db.get_agent(body.agent_id)

    if agent is None:
        # Unknown agent — return a safe, low-trust default
        return TrustObject(
            agent_id=body.agent_id,
            verified=False,
            trust_score=0,
            flags=["unregistered"],
        )

    return TrustObject(**agent)


# ── 2. POST /register ────────────────────────────────────────────────────────

@app.post("/register", response_model=RegisterResponse, status_code=201, summary="Register a new agent")
def register_agent(body: RegisterRequest):
    """
    Onboard a new agent to the PACT registry.
    Returns 409 if the agent_id or org_domain is already taken.
    """
    # Check for duplicate agent_id
    if db.get_agent(body.agent_id) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Agent '{body.agent_id}' is already registered.",
        )

    # Check for duplicate org_domain (one registry entry per organisation)
    if db.agent_domain_exists(body.org_domain):
        raise HTTPException(
            status_code=409,
            detail=f"Domain '{body.org_domain}' is already associated with a registered agent.",
        )

    db.create_agent(
        agent_id=body.agent_id,
        org_name=body.org_name,
        org_domain=body.org_domain,
        contact_email=body.contact_email,
        capabilities=body.capabilities,
        endpoint_url=body.endpoint_url,
        protocol=body.protocol,
        accepted_terms_format=body.accepted_terms_format,
        settlement_rail=body.settlement_rail,
    )

    return RegisterResponse(
        agent_id=body.agent_id,
        status="pending_review",
        message=(
            f"Agent '{body.agent_id}' has been registered and is awaiting verification. "
            "Starting trust_score is 40."
        ),
    )


# ── 3. POST /rate ────────────────────────────────────────────────────────────

@app.post("/rate", response_model=TrustObject, summary="Submit a trust rating after a transaction")
def rate_agent(body: RateRequest):
    """
    Record a 1-5 trust rating from one agent to another.
    Enforces four anti-gaming rules; returns the updated TrustObject for the rated agent.
    """
    rater = db.get_agent(body.rater_agent_id)
    rated = db.get_agent(body.rated_agent_id)

    # Both agents must exist
    if rater is None:
        raise HTTPException(status_code=404, detail=f"Rater agent '{body.rater_agent_id}' not found.")
    if rated is None:
        raise HTTPException(status_code=404, detail=f"Rated agent '{body.rated_agent_id}' not found.")

    # Rule D — an agent cannot rate itself
    if body.rater_agent_id == body.rated_agent_id:
        raise HTTPException(
            status_code=403,
            detail="An agent cannot submit a rating for itself.",
        )

    # Rule A — rater must have earned enough trust to have a credible voice
    if rater["trust_score"] < 50:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Rater '{body.rater_agent_id}' has a trust_score of {rater['trust_score']}, "
                "which is below the minimum of 50 required to submit ratings."
            ),
        )

    # Rule B — same organisation cannot rate itself (collusion block)
    if rater["org_domain"] == rated["org_domain"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Ratings between agents from the same domain ('{rater['org_domain']}') "
                "are not allowed to prevent collusion."
            ),
        )

    # Rule C — one rating per transaction
    if db.transaction_id_exists(body.transaction_id):
        raise HTTPException(
            status_code=403,
            detail=f"Transaction '{body.transaction_id}' has already been used for a rating.",
        )

    # Persist the rating — catch duplicate transaction_id from UNIQUE constraint
    # race condition (two concurrent requests passing the check above)
    try:
        db.create_rating(
            rater_agent_id=body.rater_agent_id,
            rated_agent_id=body.rated_agent_id,
            score=body.score,
            transaction_id=body.transaction_id,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=403,
            detail="Transaction has already been used for a rating.",
        )

    # Recalculate trust score with the 20%-per-domain cap applied
    new_score = db.compute_new_trust_score(
        rated_agent_id=body.rated_agent_id,
        new_score=body.score,
        rater_domain=rater["org_domain"],
    )
    db.update_agent_trust_score(body.rated_agent_id, new_score)

    # Return fresh agent record
    updated_agent = db.get_agent(body.rated_agent_id)
    return TrustObject(**updated_agent)


# ── 4. GET /agent/{agent_id} ─────────────────────────────────────────────────

@app.get("/agent/{agent_id}", response_model=AgentProfile, summary="Get full agent profile")
def get_agent_profile(agent_id: str):
    """
    Return an agent's complete record, including every rating it has received.
    """
    agent = db.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    raw_ratings = db.get_ratings_for_agent(agent_id)
    ratings = [RatingRecord(**r) for r in raw_ratings]

    return AgentProfile(**agent, ratings_received=ratings)


# ── 5. GET /registry ─────────────────────────────────────────────────────────

@app.get("/registry", response_model=list[TrustObject], summary="List all trusted agents")
def get_registry():
    """
    Public discovery endpoint — returns all verified agents with trust_score >= 50.
    """
    agents = db.get_all_verified_agents()
    return [TrustObject(**a) for a in agents]


# ── 6. POST /match ────────────────────────────────────────────────────────────

@app.post("/match", response_model=list[TrustObject], summary="Find agents by required capabilities")
def match_agents(body: MatchRequest):
    """
    Capability discovery endpoint — describe what you need, get back who can do it.
    Supports fuzzy matching: input strings are resolved through a synonym map and
    substring matching (e.g. "freight" matches "freight_booking", "shipping" matches
    "freight_booking"). Returns verified agents (trust_score >= 50) with at least one
    matching capability, ranked by match_score desc then trust_score desc.
    """
    matches = db.get_agents_with_capabilities(body.required_capabilities)
    return [TrustObject(**a) for a in matches]


# ── 7. POST /admin/verify-agent ───────────────────────────────────────────────

# Hardcoded admin key — intentional for current pre-auth stage.
# Replace with environment variable before opening to external partners.
_ADMIN_KEY = "aidress-admin-2024"


@app.post("/admin/verify-agent", response_model=TrustObject, summary="Mark an agent as verified (internal use only)")
def admin_verify_agent(body: AdminVerifyRequest):
    """
    Internal admin endpoint — sets an agent's verified flag to true.

    This endpoint is for Aidress operators only. It is not part of the public API
    and must not be exposed to or documented for external callers.
    The admin_key check is a lightweight guard for the pre-auth stage of development.
    """
    if body.admin_key != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    agent = db.get_agent(body.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{body.agent_id}' not found.")

    db.set_agent_verified(body.agent_id)

    updated = db.get_agent(body.agent_id)
    return TrustObject(**updated)
