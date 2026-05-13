from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...db.session import get_db
from ...models.plm_models import Item, ItemRevision
from ...schemas.plm_schemas import ItemCreate, Item as ItemSchema, ItemRevisionCreate
from ...core.audit_logger import log_event

router = APIRouter()

@router.get("/", response_model=List[ItemSchema])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(Item).offset(skip).limit(limit).all()
    return items

@router.post("/", response_model=ItemSchema)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    log_event(db, "system", "CREATE", "ITEM", str(db_item.id), new_val=item.model_dump())

    # Create initial revision 'A'
    initial_rev = ItemRevision(
        item_id=db_item.id,
        revision_label="A",
        lifecycle_state="IN_WORK"
    )
    db.add(initial_rev)
    db.commit()
    db.refresh(db_item)
    return db_item
