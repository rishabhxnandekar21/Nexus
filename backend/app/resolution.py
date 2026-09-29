"""Entity resolution scoring and merging. F8.

Deliberately not a trained model. Five signals with fixed, documented weights,
each of which is recorded in the candidate's `features` JSONB with the amount it
contributed - so the review queue can show *why* a pair scored what it did, and
so the number is defensible in a viva rather than being an opaque output.

    name similarity      0.35    token-based, tolerant of spelling variants
    shared phone         0.25    both records reach the same phone entity
    shared address       0.20    same location entity, or the same address text
    shared co-accused    0.10    a person both records are co-accused with
    date-of-birth        0.10    decaying with the gap, zero beyond a year
                         ----
                         1.00

Nothing ever merges on its own. A human confirms, which is a design point worth
stating out loud - see CLAUDE.md Section 5.

Scored over persons only. The other entity types carry exact identifiers - a
plate, a phone number, a case reference - where a genuine duplicate is an exact
string match rather than a judgement call, and the weights above are calibrated
for people.
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.models import Entity, Relationship, ResolutionCandidate, User

WEIGHTS: dict[str, float] = {
    "name_similarity": 0.35,
    "shared_phone": 0.25,
    "shared_address": 0.20,
    "shared_co_accused": 0.10,
    "dob_proximity": 0.10,
}
THRESHOLD = 0.60
DOB_TOLERANCE_DAYS = 365

CO_ACCUSED_TYPES = ("co_accused", "family_of")


@dataclass
class Record:
    """Everything the scorer needs about one person, gathered once."""

    id: int
    name: str
    tokens: list[str]
    dob: date | None
    address: str | None
    phones: set[int] = field(default_factory=set)
    locations: set[int] = field(default_factory=set)
    associates: set[int] = field(default_factory=set)


def tokenise(name: str) -> list[str]:
    return [part for part in name.lower().replace(".", " ").split() if part]


def name_similarity(a: list[str], b: list[str]) -> float:
    """Average best-match similarity between token lists, in both directions.

    Token-based rather than whole-string because Indian records reorder and pad
    names - "Rakesh Kumarbhai Yadav" against "Rakesh Kumar Yadhav" is the same
    person spelled two ways, and a plain string ratio understates that badly.
    Symmetric so the pair's score does not depend on which record came first.
    """
    if not a or not b:
        return 0.0

    def one_way(src: list[str], dst: list[str]) -> float:
        return sum(
            max(difflib.SequenceMatcher(None, s, d).ratio() for d in dst) for s in src
        ) / len(src)

    return (one_way(a, b) + one_way(b, a)) / 2


def _load_records(db: Session) -> dict[int, Record]:
    records: dict[int, Record] = {}
    for row in db.scalars(select(Entity).where(Entity.entity_type == "person")):
        attrs = row.attributes or {}
        raw_dob = attrs.get("dob")
        records[row.id] = Record(
            id=row.id,
            name=row.name,
            tokens=tokenise(row.name),
            dob=date.fromisoformat(raw_dob) if raw_dob else None,
            address=(attrs.get("address") or "").strip().lower() or None,
        )

    types = dict(db.execute(select(Entity.id, Entity.entity_type)).all())
    for rel in db.scalars(select(Relationship)):
        for near, far in ((rel.src_entity_id, rel.dst_entity_id),
                          (rel.dst_entity_id, rel.src_entity_id)):
            record = records.get(near)
            if record is None:
                continue
            kind = types.get(far)
            if kind == "phone":
                record.phones.add(far)
            elif kind == "location":
                record.locations.add(far)
            elif kind == "person" and rel.rel_type in CO_ACCUSED_TYPES:
                record.associates.add(far)
    return records


def score_pair(a: Record, b: Record) -> tuple[float, list[dict], str]:
    """Score one pair and explain it. Returns (score, features, reason)."""
    features: list[dict] = []
    reasons: list[str] = []

    sim = name_similarity(a.tokens, b.tokens)
    features.append({
        "name": "name_similarity", "matched": sim >= 0.5,
        "weight": WEIGHTS["name_similarity"],
        "contribution": round(WEIGHTS["name_similarity"] * sim, 4),
        "detail": f"{sim:.0%} token similarity between {a.name!r} and {b.name!r}",
    })
    if sim >= 0.5:
        reasons.append(f"names are {sim:.0%} similar")

    shared_phones = a.phones & b.phones
    features.append({
        "name": "shared_phone", "matched": bool(shared_phones),
        "weight": WEIGHTS["shared_phone"],
        "contribution": WEIGHTS["shared_phone"] if shared_phones else 0.0,
        "detail": (f"both reach phone entity {sorted(shared_phones)}"
                   if shared_phones else "no phone in common"),
    })
    if shared_phones:
        reasons.append("they share a phone")

    shared_locations = a.locations & b.locations
    same_text = bool(a.address and b.address and a.address == b.address)
    address_matched = bool(shared_locations) or same_text
    features.append({
        "name": "shared_address", "matched": address_matched,
        "weight": WEIGHTS["shared_address"],
        "contribution": WEIGHTS["shared_address"] if address_matched else 0.0,
        "detail": (f"same location entity {sorted(shared_locations)}" if shared_locations
                   else "identical address text" if same_text
                   else "no address in common"),
    })
    if address_matched:
        reasons.append("they share an address")

    # Each record is the other's own associate only if they were already linked;
    # what matters is a third person both are linked to.
    shared_associates = (a.associates & b.associates) - {a.id, b.id}
    features.append({
        "name": "shared_co_accused", "matched": bool(shared_associates),
        "weight": WEIGHTS["shared_co_accused"],
        "contribution": WEIGHTS["shared_co_accused"] if shared_associates else 0.0,
        "detail": (f"co-accused with {sorted(shared_associates)}"
                   if shared_associates else "no co-accused in common"),
    })
    if shared_associates:
        reasons.append(f"{len(shared_associates)} co-accused in common")

    if a.dob and b.dob:
        gap = abs((a.dob - b.dob).days)
        closeness = max(0.0, 1 - gap / DOB_TOLERANCE_DAYS)
        detail = f"born {gap} day{'s' if gap != 1 else ''} apart"
        if closeness > 0 and gap <= 30:
            reasons.append(detail)
    else:
        gap, closeness = None, 0.0
        detail = "date of birth missing on one record"
    features.append({
        "name": "dob_proximity", "matched": closeness > 0,
        "weight": WEIGHTS["dob_proximity"],
        "contribution": round(WEIGHTS["dob_proximity"] * closeness, 4),
        "detail": detail,
    })

    score = round(sum(f["contribution"] for f in features), 4)
    reason = ("Likely the same person: " + "; ".join(reasons) + "."
              if reasons else "Weak match on name alone.")
    return score, features, reason


def _blocks(records: dict[int, Record]) -> set[tuple[int, int]]:
    """Candidate pairs worth scoring at all.

    Comparing all 300-odd persons pairwise is ~45,000 scorings for a handful of
    real matches. Two blocking keys cut that to the plausible ones: sharing a
    name token, or sharing a phone or location. Anything that shares neither
    cannot clear the threshold - name similarity alone caps at 0.35.
    """
    by_token: dict[str, list[int]] = defaultdict(list)
    by_neighbour: dict[int, list[int]] = defaultdict(list)
    for record in records.values():
        for token in set(record.tokens):
            by_token[token].append(record.id)
        for neighbour in record.phones | record.locations:
            by_neighbour[neighbour].append(record.id)

    pairs: set[tuple[int, int]] = set()
    for group in (*by_token.values(), *by_neighbour.values()):
        ordered = sorted(group)
        for i, left in enumerate(ordered):
            for right in ordered[i + 1:]:
                pairs.add((left, right))
    return pairs


def run_resolution(db: Session) -> dict:
    """Score candidate pairs and queue the ones above the threshold.

    Idempotent: a pair that already has a row - pending, confirmed or rejected -
    is skipped, which is what makes "a rejected pair is never re-proposed"
    structural rather than a convention.
    """
    records = _load_records(db)
    existing = {
        (a, b) for a, b in db.execute(
            select(ResolutionCandidate.entity_a_id, ResolutionCandidate.entity_b_id)
        ).all()
    }

    scored = 0
    created = 0
    for left, right in sorted(_blocks(records)):
        if (left, right) in existing:
            continue
        a, b = records[left], records[right]
        scored += 1
        score, features, reason = score_pair(a, b)
        if score < THRESHOLD:
            continue
        db.add(ResolutionCandidate(
            entity_a_id=left, entity_b_id=right, score=score,
            features={"signals": features, "reason": reason, "threshold": THRESHOLD},
            status="pending",
        ))
        created += 1

    db.flush()
    return {"pairs_scored": scored, "candidates_created": created}


def confirm(db: Session, user: User, candidate: ResolutionCandidate) -> dict:
    """Merge B into A: rewire B's relationships onto A, then remove B.

    B is deleted rather than left behind with no edges, because build_graph adds
    every visible entity as a node - an edgeless B would still render, and F8
    requires that confirming visibly turns two nodes into one.

    That means the candidate rows pointing at B have to go too; the foreign keys
    do not cascade, on purpose. The permanent record of the merge is the audit
    entry written below, which names both ids and is hash-chained - a stronger
    record than a mutable queue row would have been.
    """
    keep_id, drop_id = candidate.entity_a_id, candidate.entity_b_id
    existing_edges = {
        (rel.src_entity_id, rel.dst_entity_id, rel.rel_type, rel.valid_from)
        for rel in db.scalars(select(Relationship).where(
            (Relationship.src_entity_id == keep_id) | (Relationship.dst_entity_id == keep_id)))
    }

    rewired = 0
    for rel in db.scalars(select(Relationship).where(
            (Relationship.src_entity_id == drop_id) | (Relationship.dst_entity_id == drop_id))):
        src = keep_id if rel.src_entity_id == drop_id else rel.src_entity_id
        dst = keep_id if rel.dst_entity_id == drop_id else rel.dst_entity_id
        # The edge between the two records themselves becomes a self-loop, and a
        # duplicate of one A already has adds nothing. Drop both.
        if src == dst or (src, dst, rel.rel_type, rel.valid_from) in existing_edges:
            db.delete(rel)
            continue
        rel.src_entity_id, rel.dst_entity_id = src, dst
        existing_edges.add((src, dst, rel.rel_type, rel.valid_from))
        rewired += 1

    db.flush()

    score = candidate.score
    candidate_id = candidate.id
    for row in db.scalars(select(ResolutionCandidate).where(
            (ResolutionCandidate.entity_a_id == drop_id)
            | (ResolutionCandidate.entity_b_id == drop_id))):
        db.delete(row)
    # Flush before removing the entity, not with it. models.py declares the
    # foreign keys but no ORM relationship(), so SQLAlchemy does not know
    # resolution_candidates depends on entities and is free to order the entity
    # DELETE first - which Postgres then rejects.
    db.flush()

    dropped = db.get(Entity, drop_id)
    dropped_name = dropped.name if dropped else str(drop_id)
    if dropped is not None:
        db.delete(dropped)
    db.flush()

    write_audit(db, user, "resolution_confirm", "entity", str(keep_id), {
        "candidate_id": candidate_id,
        "merged_into_id": keep_id,
        "merged_from_id": drop_id,
        "merged_from_name": dropped_name,
        "score": score,
        "relationships_rewired": rewired,
    })
    db.commit()
    return {"candidate_id": candidate_id, "status": "confirmed",
            "merged_into_id": keep_id, "relationships_rewired": rewired}


def reject(db: Session, user: User, candidate: ResolutionCandidate) -> dict:
    """Mark the pair rejected. The row stays, so run_resolution skips it forever."""
    from datetime import datetime, timezone

    candidate.status = "rejected"
    candidate.reviewed_by = user.id
    candidate.reviewed_at = datetime.now(timezone.utc)
    db.flush()
    write_audit(db, user, "resolution_reject", "resolution_candidate", str(candidate.id), {
        "entity_a_id": candidate.entity_a_id,
        "entity_b_id": candidate.entity_b_id,
        "score": candidate.score,
    })
    db.commit()
    return {"candidate_id": candidate.id, "status": "rejected",
            "merged_into_id": None, "relationships_rewired": 0}
