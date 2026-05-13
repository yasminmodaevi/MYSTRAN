from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.signature_models import ElectronicSignature
from ...models.plm_models import ItemRevision
from ...core.audit_logger import log_event
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class SignatureCreate(BaseModel):
    item_revision_id: UUID
    role: str
    reason_code: str
    comment: str = ""

@router.post("/sign")
def sign_revision(sig: SignatureCreate, db: Session = Depends(get_db)):
    rev = db.query(ItemRevision).filter(ItemRevision.id == sig.item_revision_id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Item Revision not found")

    # In a real app, verify user credentials/MFA here
    db_sig = ElectronicSignature(
        item_revision_id=sig.item_revision_id,
        user_id="current_user", # Mocked
        signature_role=sig.role,
        reason_code=sig.reason_code,
        comment=sig.comment
    )
    db.add(db_sig)

    # Log the event for AS9100 compliance
    log_event(db, "current_user", "SIGN_OFF", "REVISION", str(rev.id), new_val=sig.model_dump())

    db.commit()
    return {"status": "signed", "signed_at": db_sig.signed_at}
