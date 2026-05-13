from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.workflow_models import ChangeRequest
from ...models.plm_models import ItemRevision
from ...core.workflow_service import WorkflowService
from uuid import UUID
from datetime import datetime
import os

router = APIRouter()

BPMN_PATH = os.path.join(os.path.dirname(__file__), "../../core/workflows/design_release.bpmn")

@router.post("/start-process")
def start_design_release(rev_id: UUID, db: Session = Depends(get_db)):
    with open(BPMN_PATH, "r") as f:
        bpmn_xml = f.read()

    spec = WorkflowService.create_workflow_spec(bpmn_xml)
    workflow = WorkflowService.start_process(spec, data={"revision_id": str(rev_id)})

    # Store workflow instance ID in ChangeRequest
    cr = ChangeRequest(
        cr_id=f"CR-{rev_id}",
        title=f"Release for {rev_id}",
        workflow_instance_id=str(workflow.uuid),
        status="IN_WORK"
    )
    db.add(cr)
    db.commit()

    return {"workflow_id": workflow.uuid, "status": "Process Started"}

@router.post("/{cr_id}/approve")
def approve_change(cr_id: UUID, db: Session = Depends(get_db)):
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == cr_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change Request not found")

    cr.status = "APPROVED"

    # In a real PLM, this would trigger the actual revision status update
    # and lock the files in the vault.
    db.commit()
    return {"message": f"Change {cr.cr_id} approved and status updated."}

@router.post("/promote/{revision_id}")
def promote_revision(revision_id: UUID, db: Session = Depends(get_db)):
    rev = db.query(ItemRevision).filter(ItemRevision.id == revision_id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    if rev.lifecycle_state == "IN_WORK":
        rev.lifecycle_state = "RELEASED"
        rev.release_date = datetime.utcnow()
    elif rev.lifecycle_state == "RELEASED":
         raise HTTPException(status_code=400, detail="Revision already released")

    db.commit()
    return {"id": rev.id, "new_state": rev.lifecycle_state}
