from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .plm_models import Base
import uuid

class RequirementLink(Base):
    __tablename__ = "requirement_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    target_revision_id = Column(UUID(as_uuid=True), ForeignKey("item_revisions.id"), nullable=False)
    link_type = Column(String(50), nullable=False) # 'SATISFIED_BY', 'VERIFIED_BY'
