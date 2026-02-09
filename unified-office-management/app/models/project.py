from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, Index, Enum, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import ProjectStatus


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    duration_days = Column(Integer, nullable=False)
    justification = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    
    # Approval
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Relationships
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    members = relationship("ProjectMember", back_populates="project")
    
    __table_args__ = (
        Index("ix_project_status", "status"),
        Index("ix_project_requested_by", "requested_by_id"),
    )


class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(100), default="member")  # lead, member
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_project_member_unique", "project_id", "user_id", unique=True),
    )