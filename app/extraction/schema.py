from typing import Optional

from pydantic import BaseModel, Field


class ExtractedInvoice(BaseModel):
    vendor_name: Optional[str] = Field(
        default=None,
        description="The company that ISSUED the invoice (the seller). It may be in the header, "
                    "in a right-aligned block, or in the page footer. Not the customer being billed.")
    currency: Optional[str] = Field(
        default=None,
        description="3-letter ISO currency code (USD, EUR or GBP), shown before the amounts.")
    invoice_number: Optional[str] = Field(
        default=None, description="The invoice's own number or reference.")
    invoice_date: Optional[str] = Field(
        default=None, description="Date the invoice was issued, as YYYY-MM-DD.")
    due_date: Optional[str] = Field(
        default=None, description="Payment due date, as YYYY-MM-DD.")
    po_number: Optional[str] = Field(
        default=None, description="The customer's purchase order number.")
    subtotal: Optional[float] = Field(
        default=None, description="Sum of the line items before tax, labeled Subtotal. Plain number.")
    tax: Optional[float] = Field(
        default=None, description="Tax or VAT amount. Use 0 if the tax shown is zero. Plain number.")
    total: Optional[float] = Field(
        default=None, description="Final amount due including tax. Plain number.")