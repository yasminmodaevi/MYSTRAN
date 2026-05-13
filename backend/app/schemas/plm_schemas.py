from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class ItemBase(BaseModel):
    item_id: str
    item_type: str
    name: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemRevisionBase(BaseModel):
    revision_label: str
    lifecycle_state: Optional[str] = "IN_WORK"
    metadata_json: Optional[dict] = None

class ItemRevisionCreate(ItemRevisionBase):
    pass

class ItemRevision(ItemRevisionBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID
    created_at: Optional[datetime] = None

class Item(ItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    revisions: List[ItemRevision] = []

class BOMBase(BaseModel):
    child_item_id: UUID
    quantity: float = 1.0
    bom_type: str = "EBOM"
    find_number: Optional[int] = None

class BOMCreate(BOMBase):
    parent_rev_id: UUID

class BOMItem(BOMBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    parent_rev_id: UUID

class BOMNode(BaseModel):
    item_id: str
    name: str
    revision: str
    quantity: float
    children: List['BOMNode'] = []

BOMNode.model_rebuild()
