from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.requirement_models import RequirementLink
from ...models.plm_models import Item, ItemRevision
from uuid import UUID
from typing import List
from pydantic import BaseModel

router = APIRouter()

class TraceLinkCreate(BaseModel):
    requirement_id: UUID
    target_revision_id: UUID
    link_type: str

@router.post("/link")
def create_trace_link(link: TraceLinkCreate, db: Session = Depends(get_db)):
    # Verify requirement exists and is indeed a requirement type
    req = db.query(Item).filter(Item.id == link.requirement_id, Item.item_type == 'REQUIREMENT').first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement item not found")

    # Verify target revision exists
    target = db.query(ItemRevision).filter(ItemRevision.id == link.target_revision_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target revision not found")

    db_link = RequirementLink(**link.model_dump())
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

@router.get("/matrix/{item_id}")
def get_traceability_matrix(item_id: UUID, db: Session = Depends(get_db)):
    # Find all requirements linked to any revision of this item
    revisions = db.query(ItemRevision).filter(ItemRevision.item_id == item_id).all()
    rev_ids = [r.id for r in revisions]

    links = db.query(RequirementLink).filter(RequirementLink.target_revision_id.in_(rev_ids)).all()

    result = []
    for link in links:
        req = db.query(Item).filter(Item.id == link.requirement_id).first()
        rev = db.query(ItemRevision).filter(ItemRevision.id == link.target_revision_id).first()
        result.append({
            "requirement_id": req.item_id,
            "requirement_name": req.name,
            "target_revision": rev.revision_label,
            "link_type": link.link_type
        })
    return result
