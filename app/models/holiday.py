from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Text, Index, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin


class Holiday(Base, TimestampMixin):
    """
    Holiday model for company holidays.
    
    Only Super Admin can create/modify holidays.
    All users can view upcoming holidays.
    """
    __tablename__ = "holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Holiday details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=False, unique=True)
    
    # Type: national, company, optional
    holiday_type = Column(String(50), default="company")
    
    # Whether it's a working day (for optional holidays)
    is_optional = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Created by - using user_code
    created_by_code = Column(String(10), ForeignKey("users.user_code"), nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_code], 
                              primaryjoin="Holiday.created_by_code == User.user_code")
    
    __table_args__ = (
        Index("ix_holiday_date", "date"),
        Index("ix_holiday_active", "is_active", "date"),
    )
