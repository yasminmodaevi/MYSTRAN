from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from .plm_models import Base
import uuid
from datetime import datetime

class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cr_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20)) # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    status = Column(String(20), default="DRAFT") # 'DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED'
    workflow_instance_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
