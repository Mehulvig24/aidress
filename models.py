# models.py — Pydantic schemas for all request bodies and response shapes

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Request bodies ──────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    # The ID of the agent being looked up
    agent_id: str

class RegisterRequest(BaseModel):
    # All fields required to onboard a new agent
    agent_id:      str
    org_name:      str
    org_domain:    str
    contact_email: str

class RateRequest(BaseModel):
    # A trust rating submitted after a transaction between two agents
    rater_agent_id: str
    rated_agent_id: str
    score:          int  = Field(..., ge=1, le=5, description="Rating from 1 (terrible) to 5 (excellent)")
    transaction_id: str

class MatchRequest(BaseModel):
    # Capability query — describe what you need and PACT finds who can do it
    required_capabilities: list[str] = Field(..., min_length=1)


# ── Response shapes ─────────────────────────────────────────────────────────

class RoutingBlock(BaseModel):
    # How to reach this agent and what payment/contract formats it speaks
    endpoint_url:          Optional[str] = None   # e.g. "https://freightbot.io/api/agent"
    protocol:              Optional[str] = None   # REST | GraphQL | gRPC
    accepted_terms_format: Optional[str] = None   # JSON | XML
    settlement_rail:       Optional[str] = None   # x402 | stripe | manual

class TrustObject(BaseModel):
    # The core object PACT returns to describe an agent's trustworthiness
    agent_id:          str
    org_name:          Optional[str]  = None
    org_domain:        Optional[str]  = None
    verified:          bool
    trust_score:       int
    transaction_count: int            = 0
    flags:             list[str]      = []
    capabilities:      list[str]      = []   # what this agent can do
    registered_at:     Optional[datetime] = None
    last_active:       Optional[datetime] = None
    routing:           Optional[RoutingBlock] = None  # connection and payment details

class RegisterResponse(BaseModel):
    # Confirmation returned after a successful registration request
    agent_id: str
    status:   str   # always "pending_review" on creation
    message:  str

class RatingRecord(BaseModel):
    # A single rating entry as stored in the database
    id:             int
    rater_agent_id: str
    score:          int
    transaction_id: str
    created_at:     datetime

class AgentProfile(BaseModel):
    # Full agent record including all ratings received
    agent_id:          str
    org_name:          str
    org_domain:        str
    verified:          bool
    trust_score:       int
    transaction_count: int
    flags:             list[str]
    capabilities:      list[str]      = []   # what this agent can do
    registered_at:     datetime
    last_active:       datetime
    routing:           Optional[RoutingBlock] = None  # connection and payment details
    ratings_received:  list[RatingRecord] = []
