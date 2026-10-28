import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from sqlalchemy import func, select

from app.db import Base, Invoice, PurchaseOrder, SessionLocal, engine
from app.validation.checks import Validator
from app.validation.decision import decide

MAX_BYTES = 10 * 1024 * 1024
EXTRACTOR = os.getenv("EXTRACTOR", "ollama")


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Invoice Automation Platform", lifespan=lifespan)


def get_extractor():
    if EXTRACTOR == "rules":
        from app.extraction.rules import extract_with_rules
        return extract_with_rules
    from app.extraction.local import extract_with_ollama
    return extract_with_ollama


@app.get("/health")
def health():
    return {"status": "ok", "extractor": EXTRACTOR}


@app.post("/invoices")
async def upload_invoice(file: UploadFile = File(...)):
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (10 MB max)")
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "Only PDF files are accepted")

    start = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.pdf"
        path.write_bytes(data)
        try:
            fields = get_extractor()(path).model_dump()
        except Exception as e:
            raise HTTPException(502, f"Extraction failed: {type(e).__name__}")

    with SessionLocal() as db:
        pos = [{"po_number": p.po_number, "vendor_name": p.vendor_name,
                "approved_amount": p.approved_amount}
               for p in db.scalars(select(PurchaseOrder))]
        validator = Validator(pos)
        validator.seen = {(i.vendor_name, i.invoice_number)
                          for i in db.scalars(select(Invoice)) if i.invoice_number}
        flags = validator.check(fields)
        decision = decide(flags)

        row = Invoice(filename=file.filename or "upload.pdf",
                      vendor_name=fields["vendor_name"],
                      invoice_number=fields["invoice_number"],
                      total=fields["total"], fields=fields, flags=flags,
                      decision=decision, seconds=round(time.time() - start, 2))
        db.add(row)
        db.commit()
        return {"id": row.id, "decision": decision, "flags": flags, "fields": fields,
                "seconds": row.seconds}


@app.get("/invoices")
def list_invoices(decision: str | None = None, limit: int = 100):
    with SessionLocal() as db:
        q = select(Invoice).order_by(Invoice.id.desc()).limit(min(limit, 500))
        if decision:
            q = q.where(Invoice.decision == decision)
        return [{"id": i.id, "filename": i.filename, "vendor": i.vendor_name,
                 "invoice_number": i.invoice_number, "total": i.total,
                 "decision": i.decision, "flags": i.flags} for i in db.scalars(q)]


@app.get("/stats")
def stats():
    with SessionLocal() as db:
        rows = db.execute(select(Invoice.decision, func.count()).group_by(Invoice.decision)).all()
        counts = {d: n for d, n in rows}
        total = sum(counts.values())
        return {"total": total, "counts": counts,
                "automation_rate": round(counts.get("approve", 0) / total, 3) if total else None}
