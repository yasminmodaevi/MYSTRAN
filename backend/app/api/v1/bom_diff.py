from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models.plm_models import BOMStructure
from uuid import UUID

router = APIRouter()

@router.get("/compare/{rev_id}")
def compare_boms(rev_id: UUID, source_type: str = "EBOM", target_type: str = "MBOM", db: Session = Depends(get_db)):
    """
    Compares two BOM types for the same revision.
    """
    source_items = db.query(BOMStructure).filter(
        BOMStructure.parent_rev_id == rev_id,
        BOMStructure.bom_type == source_type
    ).all()

    target_items = db.query(BOMStructure).filter(
        BOMStructure.parent_rev_id == rev_id,
        BOMStructure.bom_type == target_type
    ).all()

    source_dict = {str(item.child_item_id): float(item.quantity) for item in source_items}
    target_dict = {str(item.child_item_id): float(item.quantity) for item in target_items}

    all_ids = set(source_dict.keys()).union(target_dict.keys())
    diffs = []

    for item_id in all_ids:
        s_qty = source_dict.get(item_id, 0)
        t_qty = target_dict.get(item_id, 0)

        if s_qty != t_qty:
            diffs.append({
                "item_id": item_id,
                "source_qty": s_qty,
                "target_qty": t_qty,
                "type": "ADDED" if s_qty == 0 else ("REMOVED" if t_qty == 0 else "QUANTITY_CHANGE")
            })

    return {"source": source_type, "target": target_type, "differences": diffs}
