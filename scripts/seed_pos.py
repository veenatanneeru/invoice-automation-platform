"""Load purchase orders from the dataset into Postgres."""
import json
from pathlib import Path

from app.db import Base, PurchaseOrder, SessionLocal, engine

Base.metadata.create_all(engine)
pos = json.loads(Path("data/labels/purchase_orders.json").read_text())
with SessionLocal() as db:
    for p in pos:
        db.merge(PurchaseOrder(**p))
    db.commit()
print(f"Loaded {len(pos)} purchase orders")
