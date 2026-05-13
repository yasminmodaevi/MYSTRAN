from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from .plm_models import Base
import uuid
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False) # In real app, UUID to users table
    action = Column(String(50), nullable=False) # 'CREATE', 'UPDATE', 'DELETE', 'SIGN_OFF'
    resource_type = Column(String(50)) # 'ITEM', 'FILE', 'BOM'
    resource_id = Column(String(100))
    old_values = Column(JSON)
    new_values = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
