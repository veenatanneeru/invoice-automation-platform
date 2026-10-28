import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from sqlalchemy import func, select

from app.db import Base, Invoice, SessionLocal, engine

MAX_BYTES = 10 * 1024 * 1024
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))


@asynccontextmanager
async def lifespan(app):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Invoice Automation Platform", lifespan=lifespan)


def view(i: Invoice) -> dict:
    return {"id": i.id, "filename": i.filename, "status": i.status, "decision": i.decision,
            "flags": i.flags, "fields": i.fields, "seconds": i.seconds,
            "attempts": i.attempts, "error": i.error}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/invoices", status_code=202)
async def upload_invoice(file: UploadFile = File(...)):
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (10 MB max)")
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "Only PDF files are accepted")

    path = UPLOAD_DIR / f"{uuid4().hex}.pdf"  # never use the client's filename on disk
    path.write_bytes(data)
    with SessionLocal() as db:
        row = Invoice(filename=(file.filename or "upload.pdf")[:200], file_path=str(path))
        db.add(row)
        db.commit()
        return {"id": row.id, "status": row.status}


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):
    with SessionLocal() as db:
        row = db.get(Invoice, invoice_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return view(row)


@app.get("/invoices")
def list_invoices(decision: str | None = None, limit: int = 100):
    with SessionLocal() as db:
        q = select(Invoice).order_by(Invoice.id.desc()).limit(min(limit, 500))
        if decision:
            q = q.where(Invoice.decision == decision)
        return [view(i) for i in db.scalars(q)]


@app.get("/stats")
def stats():
    with SessionLocal() as db:
        by_status = dict(db.execute(select(Invoice.status, func.count()).group_by(Invoice.status)).all())
        by_decision = dict(db.execute(
            select(Invoice.decision, func.count()).where(Invoice.status == "done")
            .group_by(Invoice.decision)).all())
        done = sum(by_decision.values())
        return {"queue": by_status, "decisions": by_decision, "processed": done,
                "automation_rate": round(by_decision.get("approve", 0) / done, 3) if done else None}
