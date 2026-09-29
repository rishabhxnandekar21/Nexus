"""Pydantic request and response models - the contract for every endpoint.

Shared file. Every model in CLAUDE.md Section 6 is written here up front, W1-6,
including endpoints nobody starts until Week 5, so the frontend never blocks on
the backend. Routes may return stub data; the shape they return is fixed here.

Allowed-value enums are derived from the tuples in models.py rather than
retyped, so the API and the database CHECK constraints cannot drift apart.

Convention: request models are named ...Request or ...Create, response models
...Out or ...Response. Entity ids are plain ints everywhere except inside
Cytoscape payloads, where the library requires strings.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models import ENTITY_TYPES, RESOLUTION_STATUSES, USER_ROLES

# --------------------------------------------------------------------------
# Allowed values
#
# Built from the tuples in models.py, which also build the CHECK constraints.
# One definition feeds the database, the API validation and the /docs dropdown.
# Used on request models only: responses keep plain str, so an unexpected row
# is something the UI can display rather than a 500 from response validation.
# --------------------------------------------------------------------------

EntityType = StrEnum("EntityType", {v.upper(): v for v in ENTITY_TYPES})
UserRole = StrEnum("UserRole", {v.upper(): v for v in USER_ROLES})
ResolutionStatus = StrEnum("ResolutionStatus", {v.upper(): v for v in RESOLUTION_STATUSES})


# --------------------------------------------------------------------------
# Auth  -  POST /api/auth/login, GET /api/auth/me            (W1-4, Rishabh)
# --------------------------------------------------------------------------


class UserOut(BaseModel):
    """The current user with their agency resolved, as GET /auth/me returns it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    agency_id: int
    agency_code: str
    agency_name: str


class LoginRequest(BaseModel):
    """Documented for completeness only.

    The login route takes an OAuth2 form body, not JSON, because CLAUDE.md
    Section 6 specifies a form body. This model exists so the contract is
    written down in one place.
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --------------------------------------------------------------------------
# Entities  -  GET /api/entities, /entities/{id}, POST /entities
# --------------------------------------------------------------------------


class EntitySearchResult(BaseModel):
    """One row in the search dropdown. Deliberately thin - the list can be long."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    name: str
    agency_code: str
    is_shared: bool


class EntityOut(BaseModel):
    """A full entity record. attributes is the JSONB blob; its shape varies by type."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    name: str
    attributes: dict = Field(default_factory=dict)
    agency_id: int
    agency_code: str
    source_ref: str | None = None
    is_shared: bool
    created_at: datetime


class RelationshipOut(BaseModel):
    """An edge with both endpoints named, so the panel need not resolve them."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    src_entity_id: int
    src_name: str
    dst_entity_id: int
    dst_name: str
    rel_type: str
    confidence: float
    valid_from: date
    valid_to: date | None = None
    source_case: str | None = None
    agency_code: str


class EntityDetailOut(BaseModel):
    """GET /entities/{id} - the record, its edges, and its immediate neighbours."""

    entity: EntityOut
    relationships: list[RelationshipOut] = Field(default_factory=list)
    neighbours: list[EntitySearchResult] = Field(default_factory=list)


class EntityCreate(BaseModel):
    """POST /entities, admin only. agency_id comes from the caller token."""

    entity_type: EntityType
    name: str = Field(min_length=1, max_length=200)
    attributes: dict = Field(default_factory=dict)
    source_ref: str | None = Field(default=None, max_length=100)
    is_shared: bool = False


# --------------------------------------------------------------------------
# Graph  -  GET /api/graph
#
# Cytoscape element format: {nodes: [{data: {...}}], edges: [{data: {...}}]}.
# The data wrapper is not decoration - react-cytoscapejs reads elements in
# exactly this shape. Ids are strings because Cytoscape coerces them to strings
# anyway, and an edge whose source is 7 while its node id is "7" silently fails
# to render.
# --------------------------------------------------------------------------


class GraphNodeData(BaseModel):
    id: str
    label: str
    entity_type: str
    agency_code: str
    is_shared: bool
    degree: int = 0
    attributes: dict = Field(default_factory=dict)


class GraphNode(BaseModel):
    data: GraphNodeData


class GraphEdgeData(BaseModel):
    id: str
    source: str
    target: str
    label: str
    rel_type: str
    confidence: float
    valid_from: date
    valid_to: date | None = None
    agency_code: str
    predicted: bool = False


class GraphEdge(BaseModel):
    data: GraphEdgeData


class GraphResponse(BaseModel):
    """What GraphView.jsx renders. truncated is true once the 500-node cap hits."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    center_id: int | None = None
    depth: int = 2
    truncated: bool = False


# --------------------------------------------------------------------------
# Analytics  -  GET /api/graph/analytics, /graph/path
# --------------------------------------------------------------------------


class NodeMetrics(BaseModel):
    entity_id: int
    name: str
    degree: int
    betweenness: float
    pagerank: float
    community: int


class TopConnector(BaseModel):
    """One of the five highest-betweenness nodes in view, per PRD F5."""

    entity_id: int
    name: str
    betweenness: float


class AnalyticsResponse(BaseModel):
    metrics: list[NodeMetrics] = Field(default_factory=list)
    top_connectors: list[TopConnector] = Field(default_factory=list)
    community_count: int = 0


class PathResponse(BaseModel):
    """Shortest path. found is false rather than a 404 - no path is a real answer."""

    found: bool
    entity_ids: list[int] = Field(default_factory=list)
    names: list[str] = Field(default_factory=list)
    rel_types: list[str] = Field(default_factory=list)
    length: int = 0


# --------------------------------------------------------------------------
# What-if and link prediction  -  POST /api/graph/whatif, GET /graph/predict
#
# Network impact simulation, never "crime prediction" - PRD N1 and F9.
# --------------------------------------------------------------------------


class WhatIfRequest(BaseModel):
    remove_entity_ids: list[int] = Field(min_length=1)


class ComponentStats(BaseModel):
    node_count: int
    edge_count: int
    component_count: int
    largest_component_size: int


class BetweennessShift(BaseModel):
    """A node that became more central once the removed ones were gone."""

    entity_id: int
    name: str
    before: float
    after: float
    delta: float


class WhatIfResponse(BaseModel):
    removed_entity_ids: list[int]
    before: ComponentStats
    after: ComponentStats
    top_risers: list[BetweennessShift] = Field(default_factory=list)


class PredictionOut(BaseModel):
    """One likely-but-absent link, with the shared neighbours that produced it."""

    source_entity_id: int
    target_entity_id: int
    target_name: str
    adamic_adar: float
    jaccard: float
    shared_neighbour_ids: list[int] = Field(default_factory=list)
    shared_neighbour_names: list[str] = Field(default_factory=list)


class PredictionResponse(BaseModel):
    entity_id: int
    predictions: list[PredictionOut] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Resolution  -  POST /api/resolution/run, GET /candidates, confirm, reject
# --------------------------------------------------------------------------


class ResolutionFeature(BaseModel):
    """One scoring signal and what it contributed.

    Proposed shape for the features JSONB column. Rishabh owns resolution.py and
    is free to change this - it is written now so the queue UI has a contract.
    """

    name: str
    matched: bool
    weight: float
    contribution: float
    detail: str = ""


class ResolutionCandidateOut(BaseModel):
    """A pending pair, both records inline so the queue can show them side by side."""

    id: int
    entity_a: EntityOut
    entity_b: EntityOut
    score: float
    features: list[ResolutionFeature] = Field(default_factory=list)
    reason: str = ""
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None


class ResolutionRunResponse(BaseModel):
    pairs_scored: int
    candidates_created: int


class ResolutionActionResponse(BaseModel):
    """Result of a confirm or a reject. merged_into_id is null on a reject."""

    candidate_id: int
    status: str
    merged_into_id: int | None = None
    relationships_rewired: int = 0


# --------------------------------------------------------------------------
# Natural language  -  POST /api/query/nl, /query/brief
#
# The LLM returns structured filters only. Our code runs the query. The LLM
# never emits SQL and never touches the database - PRD F10.
# --------------------------------------------------------------------------


class NLQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class NLQueryFilters(BaseModel):
    """What the LLM is allowed to return. Anything else it sends is ignored."""

    entity_types: list[str] = Field(default_factory=list)
    rel_types: list[str] = Field(default_factory=list)
    name_contains: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    agency_codes: list[str] = Field(default_factory=list)


class NLQueryResponse(BaseModel):
    interpretation: str
    filters: NLQueryFilters
    answer: str
    entity_ids: list[int] = Field(default_factory=list)
    from_cache: bool = False


class BriefRequest(BaseModel):
    entity_id: int


class BriefResponse(BaseModel):
    """A written case summary. from_cache is what keeps the demo alive offline."""

    entity_id: int
    brief: str
    from_cache: bool = False


# --------------------------------------------------------------------------
# Audit  -  GET /api/audit, /audit/verify
# --------------------------------------------------------------------------


class AuditEntryOut(BaseModel):
    """One chain row. The hashes are included so the page can show the linkage."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    seq: int
    user_id: int | None = None
    username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict = Field(default_factory=dict)
    timestamp: datetime
    prev_hash: str
    hash: str


class VerifyResponse(BaseModel):
    """broken_at_seq is the first row whose recomputed hash does not match."""

    valid: bool
    broken_at_seq: int | None = None
    checked: int


# --------------------------------------------------------------------------
# Stats  -  GET /api/stats   (F11)
# --------------------------------------------------------------------------


class TypeCount(BaseModel):
    entity_type: str
    count: int


class AgencyCount(BaseModel):
    agency_code: str
    count: int


class YearCount(BaseModel):
    year: int
    count: int


class ChainStatus(BaseModel):
    """Audit chain health. Only an admin may verify, so the verification fields
    are null for anyone else rather than absent - the page needs to tell the
    difference between "not allowed to check" and "checked and fine"."""

    rows: int
    valid: bool | None = None
    broken_at_seq: int | None = None
    checked: int | None = None
    admin_only: bool = False


class StatsResponse(BaseModel):
    """Landing-page counts, scoped to the caller like everything else."""

    scope: str
    entities: int
    relationships: int
    agencies: int
    users: int
    by_entity_type: list[TypeCount] = Field(default_factory=list)
    relationships_by_agency: list[AgencyCount] = Field(default_factory=list)
    relationships_by_year: list[YearCount] = Field(default_factory=list)
    resolution_pending: int = 0
    chain: ChainStatus
