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


# ── Response shapes ─────────────────────────────────────────────────────────

class TrustObject(BaseModel):
    # The core object PACT returns to describe an agent's trustworthiness
    agent_id:          str
    org_name:          Optional[str]  = None
    org_domain:        Optional[str]  = None
    verified:          bool
    trust_score:       int
    transaction_count: int            = 0
    flags:             list[str]      = []
    registered_at:     Optional[datetime] = None
    last_active:       Optional[datetime] = None

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
    registered_at:     datetime
    last_active:       datetime
    ratings_received:  list[RatingRecord] = []
