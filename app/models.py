from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Date, JSON, Text, Integer, Boolean, ForeignKey
from typing import Dict, List, Optional, Any

class Base(DeclarativeBase):
    pass

class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_uid: Mapped[str] = mapped_column(String(200), nullable=False, index=True, unique=True)

    # JSON dicts for localized text
    title: Mapped[Dict[str, Optional[str]]] = mapped_column(JSON, nullable=False)
    summary: Mapped[Dict[str, Optional[str]]] = mapped_column(JSON, nullable=False)
    description: Mapped[Dict[str, Optional[str]]] = mapped_column(JSON, nullable=True)

    programme: Mapped[Optional[str]] = mapped_column(String(200))
    sponsor: Mapped[Optional[str]] = mapped_column(String(200))

    # Topic or call identifiers (e.g. EU FTOP topic codes)
    topic_codes: Mapped[List[str]] = mapped_column(JSON, default=list)

    # JSON arrays
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    deadlines: Mapped[List[dict]] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    links: Mapped[dict] = mapped_column(JSON, nullable=False)

    opens_at: Mapped[Optional[str]] = mapped_column(Date)
    closes_at: Mapped[Optional[str]] = mapped_column(Date)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Store any additional metadata that doesn't have dedicated columns
    extra: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    technologies = relationship("Technology", back_populates="owner")

class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    trl: Mapped[Optional[int]] = mapped_column(Integer)  # Technology Readiness Level (1-9)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="technologies")
