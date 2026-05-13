from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from .plm_models import Base
import uuid
from datetime import datetime

class ElectronicSignature(Base):
    __tablename__ = "electronic_signatures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_revision_id = Column(UUID(as_uuid=True), ForeignKey("item_revisions.id"), nullable=False)
    user_id = Column(String(100), nullable=False)
    signature_role = Column(String(50)) # 'AUTHOR', 'REVIEWER', 'APPROVER'
    reason_code = Column(String(100)) # e.g., 'DESIGN_APPROVAL'
    signed_at = Column(DateTime, default=datetime.utcnow)
    comment = Column(Text)
