from datetime import datetime, date
from typing import Optional
from sqlalchemy import (String, Integer, ForeignKey, Text, DateTime, Date, Boolean,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class RegistrationRequest(Base):
    __tablename__ = "registration_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    message: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    processed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(100), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

class Delo(Base):
    __tablename__ = "delos"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    index_code: Mapped[str] = mapped_column(String(50))
    base_title: Mapped[str] = mapped_column(Text)
    year: Mapped[int] = mapped_column(Integer)
    retention: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("index_code", "year", name="ux_delos_index_year"),
    )

class Tom(Base):
    __tablename__ = "toms"
    id: Mapped[int] = mapped_column(primary_key=True)
    delo_id: Mapped[int] = mapped_column(ForeignKey("delos.id", ondelete="CASCADE"))
    tom_number: Mapped[int] = mapped_column(Integer)
    max_pages: Mapped[int] = mapped_column(Integer, default=250)
    status: Mapped[str] = mapped_column(String(20), default="open")
    __table_args__ = (
        UniqueConstraint("delo_id", "tom_number", name="ux_toms_delo_number"),
    )

class ExternalDocumentStaging(Base):
    __tablename__ = "external_documents_staging"
    external_ref: Mapped[str] = mapped_column(String(200), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    account_number: Mapped[Optional[str]] = mapped_column(String(100))
    page_count: Mapped[int] = mapped_column(Integer)
    
    incoming_num: Mapped[Optional[str]] = mapped_column(String(100))
    incoming_date: Mapped[Optional[date]] = mapped_column(Date)
    outgoing_num: Mapped[Optional[str]] = mapped_column(String(100))
    outgoing_date: Mapped[Optional[date]] = mapped_column(Date)
    copy_num: Mapped[Optional[str]] = mapped_column(String(50), default="1")
    cipher: Mapped[Optional[str]] = mapped_column(String(100))
    grif: Mapped[Optional[str]] = mapped_column(String(100))
    organ: Mapped[Optional[str]] = mapped_column(Text)
    doc_num: Mapped[Optional[str]] = mapped_column(String(100))
    employee: Mapped[Optional[str]] = mapped_column(String(100))

    synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

class DocumentType(Base):
    __tablename__ = "document_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    tom_id: Mapped[int] = mapped_column(ForeignKey("toms.id"))
    title: Mapped[str] = mapped_column(Text)
    account_number: Mapped[Optional[str]] = mapped_column(String(100))
    page_count: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    order_in_tom: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20))
    external_ref: Mapped[Optional[str]] = mapped_column(String(200))
    type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document_types.id"))
    
    incoming_num: Mapped[Optional[str]] = mapped_column(String(100))
    incoming_date: Mapped[Optional[date]] = mapped_column(Date)
    outgoing_num: Mapped[Optional[str]] = mapped_column(String(100))
    outgoing_date: Mapped[Optional[date]] = mapped_column(Date)
    copy_num: Mapped[Optional[str]] = mapped_column(String(50))
    cipher: Mapped[Optional[str]] = mapped_column(String(100))
    grif: Mapped[Optional[str]] = mapped_column(String(100))
    organ: Mapped[Optional[str]] = mapped_column(Text)
    doc_num: Mapped[Optional[str]] = mapped_column(String(100))
    employee: Mapped[Optional[str]] = mapped_column(String(100))

    original_title: Mapped[Optional[str]] = mapped_column(Text)
    original_doc_num: Mapped[Optional[str]] = mapped_column(String(100))
    original_organ: Mapped[Optional[str]] = mapped_column(Text)
    original_incoming_num: Mapped[Optional[str]] = mapped_column(String(100))
    original_incoming_date: Mapped[Optional[date]] = mapped_column(Date)
    original_outgoing_num: Mapped[Optional[str]] = mapped_column(String(100))
    original_outgoing_date: Mapped[Optional[date]] = mapped_column(Date)
    original_copy_num: Mapped[Optional[str]] = mapped_column(String(50))
    original_cipher: Mapped[Optional[str]] = mapped_column(String(100))
    original_employee: Mapped[Optional[str]] = mapped_column(String(100))
    original_page_count: Mapped[Optional[int]] = mapped_column(Integer)

    placed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("tom_id", "order_in_tom", name="ux_documents_order"),
        UniqueConstraint("tom_id", "page_start", name="ux_documents_page_start"),
    )

class DocumentChange(Base):
    __tablename__ = "document_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    user_login: Mapped[Optional[str]] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(20), default="user")
    field_name: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class PlacementDraft(Base):
    __tablename__ = "placement_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    delo_id: Mapped[int] = mapped_column(ForeignKey("delos.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("user_id", "delo_id", name="ux_drafts_user_delo"),
    )

class PlacementDraftItem(Base):
    __tablename__ = "placement_draft_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("placement_drafts.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20))
    external_ref: Mapped[Optional[str]] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(Text)
    account_number: Mapped[Optional[str]] = mapped_column(String(100))
    page_count: Mapped[int] = mapped_column(Integer)
    type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("document_types.id"))
    
    incoming_num: Mapped[Optional[str]] = mapped_column(String(100))
    incoming_date: Mapped[Optional[date]] = mapped_column(Date)
    outgoing_num: Mapped[Optional[str]] = mapped_column(String(100))
    outgoing_date: Mapped[Optional[date]] = mapped_column(Date)
    copy_num: Mapped[Optional[str]] = mapped_column(String(50))
    cipher: Mapped[Optional[str]] = mapped_column(String(100))
    grif: Mapped[Optional[str]] = mapped_column(String(100))
    organ: Mapped[Optional[str]] = mapped_column(Text)
    doc_num: Mapped[Optional[str]] = mapped_column(String(100))
    employee: Mapped[Optional[str]] = mapped_column(String(100))
    
    original_title: Mapped[Optional[str]] = mapped_column(Text)
    original_doc_num: Mapped[Optional[str]] = mapped_column(String(100))
    original_organ: Mapped[Optional[str]] = mapped_column(Text)
    original_page_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    __table_args__ = (
        UniqueConstraint("draft_id", "position", name="ux_draft_items_position"),
    )
