"""Background worker: claims queued invoices from Postgres and processes them."""
import os
import time
from pathlib import Path

from sqlalchemy import select

from app.db import Base, Invoice, PurchaseOrder, SessionLocal, engine
from app.security.scanner import scan_pdf
from app.validation.checks import Validator
from app.validation.decision import decide

MAX_ATTEMPTS = 3
EXTRACTOR = os.getenv("EXTRACTOR", "ollama")


def get_extractor():
    if EXTRACTOR == "rules":
        from app.extraction.rules import extract_with_rules
        return extract_with_rules
    from app.extraction.local import extract_with_ollama
    return extract_with_ollama


def claim():
    """Atomically take one queued job. SKIP LOCKED lets several workers run safely."""
    with SessionLocal() as db:
        job = db.scalars(select(Invoice).where(Invoice.status == "queued")
                         .order_by(Invoice.id).with_for_update(skip_locked=True).limit(1)).first()
        if job is None:
            return None
        job.status = "processing"
        job.attempts += 1
        db.commit()
        return job.id, job.file_path


def fail_or_retry(job_id, err):
    with SessionLocal() as db:
        job = db.get(Invoice, job_id)
        job.error = f"{type(err).__name__}: {err}"[:500]
        job.status = "failed" if job.attempts >= MAX_ATTEMPTS else "queued"
        db.commit()


def handle(job_id, path, extract):
    start = time.time()
    try:
        fields = extract(Path(path)).model_dump()
    except Exception as e:
        fail_or_retry(job_id, e)
        print(f"job {job_id}: extraction error ({type(e).__name__})")
        return

    with SessionLocal() as db:
        pos = [{"po_number": p.po_number, "vendor_name": p.vendor_name,
                "approved_amount": p.approved_amount} for p in db.scalars(select(PurchaseOrder))]
        validator = Validator(pos)
        validator.seen = {(i.vendor_name, i.invoice_number) for i in
                          db.scalars(select(Invoice).where(Invoice.status == "done"))
                          if i.invoice_number}
        flags = validator.check(fields) + scan_pdf(Path(path))

        job = db.get(Invoice, job_id)
        job.fields, job.flags = fields, flags
        job.vendor_name, job.invoice_number, job.total = (
            fields["vendor_name"], fields["invoice_number"], fields["total"])
        job.decision = decide(flags)
        job.seconds = round(time.time() - start, 2)
        job.error = None
        job.status = "done"
        db.commit()
        print(f"job {job_id}: {job.decision} {flags} in {job.seconds}s")


def main():
    Base.metadata.create_all(engine)
    extract = get_extractor()
    print(f"worker started (extractor={EXTRACTOR})")
    while True:
        claimed = claim()
        if claimed is None:
            time.sleep(2)
            continue
        handle(*claimed, extract)


if __name__ == "__main__":
    main()
