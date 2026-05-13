from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.plm_models import FileVault, ItemRevision
from ...core.fea_parser import parse_nastran_f06
from uuid import UUID
import os

router = APIRouter()

@router.post("/process/{file_id}")
async def process_fea_results(file_id: UUID, db: Session = Depends(get_db)):
    file_record = db.query(FileVault).filter(FileVault.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in vault")

    if not file_record.file_name.endswith('.f06'):
        raise HTTPException(status_code=400, detail="Only Nastran .f06 files are supported for parsing")

    if not os.path.exists(file_record.file_path):
         raise HTTPException(status_code=404, detail="Physical file missing on NAS")

    with open(file_record.file_path, "r") as f:
        content = f.read()

    metrics = parse_nastran_f06(content)

    # Update Item Revision metadata
    rev = db.query(ItemRevision).filter(ItemRevision.id == file_record.item_revision_id).first()
    if rev:
        if not rev.metadata_json:
            rev.metadata_json = {}

        # Merge metrics into metadata
        rev.metadata_json["fea_metrics"] = metrics
        db.commit()

    return {"status": "success", "metrics": metrics}
