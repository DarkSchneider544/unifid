from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, Index, Enum, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import ProjectStatus


class Project(Base, TimestampMixin):
    """
    Project management.
    Uses user_code instead of user_id.
    """
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Project details
    project_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    
    # Requester - using user_code
    requested_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Timeline
    duration_days = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    justification = Column(Text, nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    
    # Approval - using user_code
    approved_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Relationships
    requested_by = relationship("User", foreign_keys=[requested_by_code], primaryjoin="Project.requested_by_code == User.user_code")
    approved_by = relationship("User", foreign_keys=[approved_by_code], primaryjoin="Project.approved_by_code == User.user_code")
    members = relationship("ProjectMember", back_populates="project")
    
    __table_args__ = (
        Index("ix_project_status", "status"),
        Index("ix_project_requested_by", "requested_by_code"),
    )


class ProjectMember(Base, TimestampMixin):
    """
    Project team members.
    Uses user_code instead of user_id.
    """
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Project reference
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Member - using user_code
    user_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Role in project
    role = Column(String(100), default="member")  # lead, member, observer
    
    # Status
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    left_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", foreign_keys=[user_code], primaryjoin="ProjectMember.user_code == User.user_code")
    
    __table_args__ = (
        Index("ix_project_member_unique", "project_id", "user_code", unique=True),
        Index("ix_project_member_user", "user_code", "is_active"),
    )