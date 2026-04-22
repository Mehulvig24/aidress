# taxonomy.py — Capability taxonomy and synonym mapping for fuzzy /match resolution
#
# Defines the canonical set of capability tags organised by category,
# plus a synonym map that lets callers use informal terms like "freight"
# or "shipping" and still find agents tagged with "freight_booking".

# ── Canonical capability tags grouped by vertical ────────────────────────────

TAXONOMY: dict[str, list[str]] = {
    "LOGISTICS": [
        "freight_booking",
        "shipment_tracking",
        "carrier_negotiation",
        "port_coordination",
        "container_management",
        "yard_scheduling",
        "vessel_tracking",
        "route_optimisation",
        "last_mile_delivery",
        "fleet_dispatch",
        "bill_of_lading",
    ],
    "FINANCE": [
        "trade_finance",
        "payment_settlement",
        "invoice_reconciliation",
        "credit_assessment",
        "escrow_management",
        "currency_conversion",
    ],
    "COMPLIANCE": [
        "customs_clearance",
        "compliance_check",
        "regulatory_reporting",
        "kyc_verification",
        "certificate_issuance",
        "sanctions_screening",
        "cargo_verification",
        "document_validation",
    ],
    "DATA": [
        "demand_forecasting",
        "inventory_sync",
        "supplier_onboarding",
        "purchase_order_management",
        "schedule_management",
        "analytics_reporting",
        "data_enrichment",
    ],
}

# Flat set of every canonical tag — used for fast membership checks
ALL_TAGS: set[str] = {tag for tags in TAXONOMY.values() for tag in tags}

# ── Synonym map ──────────────────────────────────────────────────────────────
# Maps informal, abbreviated, or alternative terms to the canonical tag.
# Keys are lowercase. Checked before partial-match fallback.

SYNONYMS: dict[str, str] = {
    # Logistics
    "shipping":     "freight_booking",
    "freight":      "freight_booking",
    "tracking":     "shipment_tracking",
    "track":        "shipment_tracking",
    "negotiate":    "carrier_negotiation",
    "negotiation":  "carrier_negotiation",
    "port":         "port_coordination",
    "container":    "container_management",
    "warehouse":    "yard_scheduling",
    "yard":         "yard_scheduling",
    "vessel":       "vessel_tracking",
    "ship":         "vessel_tracking",
    "routing":      "route_optimisation",
    "route":        "route_optimisation",
    "delivery":     "last_mile_delivery",
    "last mile":    "last_mile_delivery",
    "dispatch":     "fleet_dispatch",
    "fleet":        "fleet_dispatch",
    "bol":          "bill_of_lading",
    "lading":       "bill_of_lading",
    # Finance
    "finance":      "trade_finance",
    "trade":        "trade_finance",
    "payment":      "payment_settlement",
    "pay":          "payment_settlement",
    "invoice":      "invoice_reconciliation",
    # Compliance
    "customs":      "customs_clearance",
    "clearance":    "customs_clearance",
    "compliance":   "compliance_check",
    "regulatory":   "regulatory_reporting",
    "kyc":          "kyc_verification",
    "verification": "cargo_verification",
    "certificate":  "certificate_issuance",
    "cert":         "certificate_issuance",
    "sanctions":    "sanctions_screening",
    "screening":    "sanctions_screening",
    "document":     "document_validation",
    "docs":         "document_validation",
    # Data
    "forecast":     "demand_forecasting",
    "demand":       "demand_forecasting",
    "inventory":    "inventory_sync",
    "stock":        "inventory_sync",
    "supplier":     "supplier_onboarding",
    "onboarding":   "supplier_onboarding",
    "purchase order": "purchase_order_management",
    "po":           "purchase_order_management",
}


# ── Resolution helper ────────────────────────────────────────────────────────

def normalize_capability(raw: str) -> list[str]:
    """
    Resolve a raw capability string to one or more canonical tags.

    Resolution order:
      1. Exact synonym lookup   — "freight" → ["freight_booking"]
      2. Exact canonical match  — "freight_booking" → ["freight_booking"]
      3. Substring match        — "freight" would also hit here, matching any
         canonical tag that contains the raw string as a substring
      4. No match               — returns []

    Returns a list because a substring like "track" could match multiple tags
    (e.g. shipment_tracking, vessel_tracking).
    """
    term = raw.strip().lower()
    if not term:
        return []

    # 1. Synonym lookup — exact hit on the informal term
    if term in SYNONYMS:
        return [SYNONYMS[term]]

    # 2. Already a canonical tag
    if term in ALL_TAGS:
        return [term]

    # 3. Substring match — "freight" matches "freight_booking"
    matches = [tag for tag in ALL_TAGS if term in tag]
    return matches
