from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Date, JSON, Text

class Base(DeclarativeBase):
    pass

class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_uid: Mapped[str] = mapped_column(String(200), nullable=False, index=True, unique=True)
    title: Mapped[dict] = mapped_column(JSON, nullable=False)     # {"sv":..., "en":...}
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)   # {"sv":..., "en":...}
    programme: Mapped[str | None] = mapped_column(String(200))
    sponsor: Mapped[str | None] = mapped_column(String(200))
    tags: Mapped[dict] = mapped_column(JSON, default=list)        # ["electric aviation", ...]
    deadlines: Mapped[dict] = mapped_column(JSON, default=list)   # [{"type":"single","date":"YYYY-MM-DD"}]
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    links: Mapped[dict] = mapped_column(JSON, nullable=False)
    opens_at: Mapped[str | None] = mapped_column(Date)
    closes_at: Mapped[str | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
