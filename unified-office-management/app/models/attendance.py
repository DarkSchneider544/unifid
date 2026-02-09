from sqlalchemy import (
    Column, String, DateTime, Date, ForeignKey, Text, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin
from .enums import AttendanceStatus


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.DRAFT)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    entries = relationship("AttendanceEntry", back_populates="attendance", order_by="AttendanceEntry.check_in")
    
    __table_args__ = (
        Index("ix_attendance_user_date", "user_id", "date", unique=True),
        Index("ix_attendance_status", "status"),
    )


class AttendanceEntry(Base, TimestampMixin):
    __tablename__ = "attendance_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attendance_id = Column(UUID(as_uuid=True), ForeignKey("attendances.id"), nullable=False)
    check_in = Column(DateTime(timezone=True), nullable=False)
    check_out = Column(DateTime(timezone=True), nullable=True)
    entry_type = Column(String(50), default="regular")  # regular, break, overtime
    notes = Column(Text, nullable=True)
    
    # Relationships
    attendance = relationship("Attendance", back_populates="entries")