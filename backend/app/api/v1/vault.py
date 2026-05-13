from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import os
import shutil
import hashlib
from ...db.session import get_db
from ...models.plm_models import FileVault, ItemRevision
from uuid import UUID

router = APIRouter()

# Simulated NAS path
VAULT_BASE_PATH = os.getenv("VAULT_PATH", "./vault")

if not os.path.exists(VAULT_BASE_PATH):
    os.makedirs(VAULT_BASE_PATH)

@router.post("/upload/{revision_id}")
async def upload_file(
    revision_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Check if revision exists
    rev = db.query(ItemRevision).filter(ItemRevision.id == revision_id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Item Revision not found")

    # Path logic: vault/revision_id/filename
    rev_path = os.path.join(VAULT_BASE_PATH, str(revision_id))
    if not os.path.exists(rev_path):
        os.makedirs(rev_path)

    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(rev_path, safe_filename)
    sha256_hash = hashlib.sha256()

    # Save file to NAS using streaming to handle large CAD/CAE files
    with open(file_path, "wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024) # 1MB chunks
            if not chunk:
                break
            sha256_hash.update(chunk)
            buffer.write(chunk)

    file_hash = sha256_hash.hexdigest()

    # Save metadata to DB
    db_file = FileVault(
        item_revision_id=revision_id,
        file_name=file.filename,
        file_path=file_path,
        file_hash=file_hash,
        file_type=file.filename.split('.')[-1].upper() if '.' in file.filename else "UNKNOWN"
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return {"id": db_file.id, "file_name": db_file.file_name, "hash": db_file.file_hash}
