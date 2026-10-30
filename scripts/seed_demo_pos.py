"""Create purchase orders for the hard dataset so the demo shows a realistic mix of outcomes."""
import json
from pathlib import Path

from app.db import Base, PurchaseOrder, SessionLocal, engine

Base.metadata.create_all(engine)
labels = json.loads(Path("data/labels/labels_hard.json").read_text())
counts = {"clean": 0, "no_po": 0, "over_budget": 0, "vendor_mismatch": 0}

with SessionLocal() as db:
    for i, lab in enumerate(labels):
        f = lab["fields"]
        kind = i % 10
        if kind in (0, 1):  # no purchase order on file
            counts["no_po"] += 1
            continue
        amount, vendor = f["total"], f["vendor_name"]
        if kind == 2:  # invoice exceeds the approved amount
            amount = round(f["total"] / 1.2, 2)
            counts["over_budget"] += 1
        elif kind == 3:  # PO belongs to a different vendor
            vendor = "Different Supplier Ltd"
            counts["vendor_mismatch"] += 1
        else:
            counts["clean"] += 1
        db.merge(PurchaseOrder(po_number=f["po_number"], vendor_name=vendor,
                               approved_amount=amount))
    db.commit()
print("Purchase orders created for the hard set:", counts)
