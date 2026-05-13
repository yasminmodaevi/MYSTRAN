from sqlalchemy.orm import Session
from ..models.audit_models import AuditLog

def log_event(db: Session, user_id: str, action: str, resource_type: str, resource_id: str, old_val: dict = None, new_val: dict = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_val,
        new_values=new_val
    )
    db.add(log)
    db.commit()
