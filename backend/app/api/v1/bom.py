from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...db.session import get_db
from ...models.plm_models import BOMStructure, ItemRevision, Item
from ...schemas.plm_schemas import BOMCreate, BOMItem, BOMNode
from uuid import UUID

router = APIRouter()

@router.post("/", response_model=BOMItem)
def add_to_bom(bom: BOMCreate, db: Session = Depends(get_db)):
    # Verify parent revision exists
    parent = db.query(ItemRevision).filter(ItemRevision.id == bom.parent_rev_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent revision not found")

    # Verify child item exists
    child = db.query(Item).filter(Item.id == bom.child_item_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child item not found")

    db_bom = BOMStructure(**bom.model_dump())
    db.add(db_bom)
    db.commit()
    db.refresh(db_bom)
    return db_bom

@router.get("/{rev_id}", response_model=BOMNode)
def get_bom_hierarchy(rev_id: UUID, bom_type: str = "EBOM", db: Session = Depends(get_db)):
    rev = db.query(ItemRevision).filter(ItemRevision.id == rev_id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    item = db.query(Item).filter(Item.id == rev.item_id).first()

    node = BOMNode(
        item_id=item.item_id,
        name=item.name,
        revision=rev.revision_label,
        quantity=1.0,
        children=[]
    )

    # Recursive helper to build the tree
    def build_tree(current_rev_id: UUID, current_node: BOMNode):
        children_links = db.query(BOMStructure).filter(
            BOMStructure.parent_rev_id == current_rev_id,
            BOMStructure.bom_type == bom_type
        ).all()

        for link in children_links:
            child_item = db.query(Item).filter(Item.id == link.child_item_id).first()
            # For simplicity, resolve latest revision of child
            # In a real PLM, this would use BOM Resolution Rules (e.g., 'Latest Released')
            child_rev = db.query(ItemRevision).filter(
                ItemRevision.item_id == child_item.id
            ).order_by(ItemRevision.revision_label.desc()).first()

            if child_rev:
                child_node = BOMNode(
                    item_id=child_item.item_id,
                    name=child_item.name,
                    revision=child_rev.revision_label,
                    quantity=float(link.quantity),
                    children=[]
                )
                current_node.children.append(child_node)
                build_tree(child_rev.id, child_node)

    build_tree(rev_id, node)
    return node
