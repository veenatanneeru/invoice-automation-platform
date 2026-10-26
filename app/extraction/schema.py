from typing import Optional

from pydantic import BaseModel


class ExtractedInvoice(BaseModel):
    vendor_name: Optional[str] = None
    currency: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None