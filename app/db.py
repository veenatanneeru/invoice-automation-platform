import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import JSON, DateTime, Float, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()

URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/invoices")
URL = URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_number: Mapped[str] = mapped_column(String, primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String)
    approved_amount: Mapped[float] = mapped_column(Float)


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    vendor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String, nullable=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    fields: Mapped[dict] = mapped_column(JSON)
    flags: Mapped[list] = mapped_column(JSON)
    decision: Mapped[str] = mapped_column(String, index=True)
    seconds: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
