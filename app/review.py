"""Human review: queue of flagged invoices, PDF viewer, and approve/reject endpoint."""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db import Invoice, SessionLocal

router = APIRouter()


class ReviewIn(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    note: str = Field(default="", max_length=500)


@router.get("/review/queue")
def review_queue():
    with SessionLocal() as db:
        q = (select(Invoice)
             .where(Invoice.status == "done", Invoice.decision == "review",
                    Invoice.review_action.is_(None))
             .order_by(Invoice.id).limit(100))
        return [{"id": i.id, "fields": i.fields, "flags": i.flags} for i in db.scalars(q)]


@router.get("/invoices/{invoice_id}/file")
def invoice_file(invoice_id: int):
    with SessionLocal() as db:
        row = db.get(Invoice, invoice_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return FileResponse(row.file_path, media_type="application/pdf")


@router.post("/invoices/{invoice_id}/review")
def submit_review(invoice_id: int, body: ReviewIn):
    with SessionLocal() as db:
        row = db.get(Invoice, invoice_id)
        if row is None:
            raise HTTPException(404, "Not found")
        if row.status != "done" or row.decision != "review":
            raise HTTPException(409, "This invoice is not awaiting review")
        if row.review_action:
            raise HTTPException(409, "Already reviewed")
        row.review_action = body.action
        row.review_note = body.note
        row.reviewed_at = datetime.utcnow()
        db.commit()
        return {"id": row.id, "review_action": row.review_action}


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Invoice review</title>
<style>
body{font-family:system-ui,sans-serif;margin:2rem auto;max-width:900px;padding:0 1rem}
.card{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}
.flag{background:#fde8e8;border-radius:4px;padding:2px 8px;margin-right:6px;font-size:.85rem}
button{margin-right:8px;padding:6px 14px;cursor:pointer}
td{padding:2px 14px 2px 0}
</style></head><body>
<h1>Invoices awaiting review</h1>
<div id="list">Loading…</div>
<script>
async function load() {
  const r = await fetch('/review/queue');
  const items = await r.json();
  const list = document.getElementById('list');
  list.replaceChildren();
  if (!items.length) { list.textContent = 'Nothing waiting for review.'; return; }
  for (const it of items) {
    const card = document.createElement('div'); card.className = 'card';
    const h = document.createElement('h3');
    h.textContent = '#' + it.id + ' · ' + (it.fields.vendor_name || '(unknown vendor)') +
                    ' · ' + (it.fields.invoice_number || 'no number');
    card.appendChild(h);
    const fl = document.createElement('div');
    for (const f of it.flags) {
      const s = document.createElement('span'); s.className = 'flag'; s.textContent = f; fl.appendChild(s);
    }
    card.appendChild(fl);
    const t = document.createElement('table');
    for (const [k, v] of Object.entries(it.fields)) {
      const tr = t.insertRow();
      tr.insertCell().textContent = k;
      tr.insertCell().textContent = (v === null ? '—' : v);
    }
    card.appendChild(t);
    const a = document.createElement('a');
    a.href = '/invoices/' + it.id + '/file'; a.target = '_blank'; a.textContent = 'Open PDF';
    card.appendChild(a);
    const note = document.createElement('input');
    note.placeholder = 'Note (optional)'; note.maxLength = 500;
    note.style.cssText = 'display:block;margin:8px 0;width:100%';
    card.appendChild(note);
    for (const act of ['approve', 'reject']) {
      const b = document.createElement('button'); b.textContent = act;
      b.onclick = async () => {
        await fetch('/invoices/' + it.id + '/review', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({action: act, note: note.value})});
        load();
      };
      card.appendChild(b);
    }
    list.appendChild(card);
  }
}
load();
</script></body></html>"""


@router.get("/review", response_class=HTMLResponse)
def review_page():
    return PAGE