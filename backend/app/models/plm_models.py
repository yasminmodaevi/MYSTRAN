from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, DECIMAL, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(String(50), unique=True, nullable=False)
    item_type = Column(String(20), nullable=False) # 'PART', 'DOCUMENT', 'REQUIREMENT'
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    revisions = relationship("ItemRevision", back_populates="item")

class ItemRevision(Base):
    __tablename__ = "item_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"))
    revision_label = Column(String(10), nullable=False) # 'A', 'B', etc.
    lifecycle_state = Column(String(20), default="IN_WORK")
    effective_date = Column(DateTime)
    release_date = Column(DateTime)
    change_notice_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_json = Column(JSON) # Stores specific attributes like mass, FEA summary

    item = relationship("Item", back_populates="revisions")
    vault_files = relationship("FileVault", back_populates="revision")

class BOMStructure(Base):
    __tablename__ = "bom_structures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_rev_id = Column(UUID(as_uuid=True), ForeignKey("item_revisions.id"))
    child_item_id = Column(UUID(as_uuid=True), ForeignKey("items.id"))
    quantity = Column(DECIMAL, nullable=False, default=1.0)
    bom_type = Column(String(10), nullable=False) # 'EBOM', 'MBOM', 'SBOM'
    find_number = Column(Integer)

class FileVault(Base):
    __tablename__ = "file_vault"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_revision_id = Column(UUID(as_uuid=True), ForeignKey("item_revisions.id"))
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(20)) # 'CAD_MODEL', 'FEA_RESULT', etc.
    file_hash = Column(String(255), nullable=False)
    is_latest = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    revision = relationship("ItemRevision", back_populates="vault_files")
