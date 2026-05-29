"""SQLAlchemy ORM models with soft delete and performance optimizations."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, ForeignKey, String, Text, text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.session import Base


class UserRole(str, Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class User(Base):
    """User account with soft delete support."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default=UserRole.USER, server_default=text("'user'"),
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("NOW()"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)  # Soft delete

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", lazy="selectin",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", lazy="selectin",
    )

    __table_args__ = (
        Index('idx_user_email', 'email', postgresql_where=text("deleted_at IS NULL")),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Document(Base):
    """Uploaded document with denormalized counters."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Required
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO path
    status: Mapped[str] = mapped_column(
        String(50), default=DocumentStatus.UPLOADING, server_default=text("'uploading'"),
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    chunk_count: Mapped[int] = mapped_column(  # Denormalized for performance
        default=0, server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("NOW()"),
        onupdate=datetime.utcnow,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)  # Soft delete

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", lazy="selectin", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index('idx_document_user', 'user_id', 'created_at', postgresql_where=text("deleted_at IS NULL")),
        Index('idx_document_status', 'status', postgresql_where=text("status = 'processing'")),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename})>"


class DocumentChunk(Base):
    """Document chunk with metadata for retrieval and citations."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)  # Position in document
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(  # For ContextBuilder budgeting
        default=0, server_default=text("0"),
    )
    meta_data: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"),
    )
    embedding_model: Mapped[str] = mapped_column(  # Track which model created embedding
        String(100), default="", server_default=text("''"),
    )
    qdrant_point_id: Mapped[str | None] = mapped_column(  # For Qdrant deletion
        String(255), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("NOW()"),
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index('idx_chunk_document', 'document_id'),
        Index('idx_chunk_document_order', 'document_id', 'chunk_index'),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, idx={self.chunk_index})>"


class Conversation(Base):
    """Chat conversation with denormalized message count."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message_count: Mapped[int] = mapped_column(  # Denormalized for performance
        default=0, server_default=text("0"),
    )
    last_message_at: Mapped[datetime | None] = mapped_column(nullable=True)  # For sorting
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("NOW()"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)  # Soft delete

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", lazy="selectin", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index(
            'idx_conversation_user',
            'user_id', text('last_message_at DESC NULLS LAST'), text('created_at DESC'),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base):
    """Message in conversation with citation sources."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # USER, ASSISTANT, SYSTEM
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[dict] = mapped_column(  # [{doc_id, chunk_id, score, text_snippet}]
        JSONB, default=list, server_default=text("'[]'::jsonb"),
    )
    token_count: Mapped[int | None] = mapped_column(nullable=True)  # For analytics
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=text("NOW()"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index('idx_message_conversation', 'conversation_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"
