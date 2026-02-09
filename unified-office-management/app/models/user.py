from sqlalchemy import (
    Column, String, Boolean, Enum, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import UserRole, ManagerDomain


class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    manager_domain = Column(Enum(ManagerDomain), nullable=True)
    is_team_lead = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Relationships
    team_lead_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    team_lead = relationship("User", remote_side=[id], foreign_keys=[team_lead_id])
    manager = relationship("User", remote_side=[id], foreign_keys=[manager_id])
    
    # Indexes
    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_active_deleted", "is_active", "is_deleted"),
    )
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"