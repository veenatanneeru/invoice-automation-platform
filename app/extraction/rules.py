"""Baseline extractor: PDF text + regex. Free, fast, and brittle on purpose."""
import re
from pathlib import Path

import pdfplumber

from app.extraction.schema import ExtractedInvoice

AMOUNT = r"[A-Z]{3}\s*([\d,]+\.\d{2})"


def pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def _num(m):
    return float(m.group(1).replace(",", "")) if m else None


def extract_with_rules(path: Path) -> ExtractedInvoice:
    text = pdf_text(path)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    vendor = None
    if lines:
        vendor = re.sub(r"\s*INVOICE\s*$", "", lines[0]).strip() or None

    dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    inv_no = re.search(r"INV-\d{5}", text)
    po = re.search(r"PO-\d{6}", text)
    cur = re.search(r"\b(USD|EUR|GBP)\b", text)

    return ExtractedInvoice(
        vendor_name=vendor,
        currency=cur.group(1) if cur else None,
        invoice_number=inv_no.group(0) if inv_no else None,
        invoice_date=dates[0] if len(dates) > 0 else None,
        due_date=dates[1] if len(dates) > 1 else None,
        po_number=po.group(0) if po else None,
        subtotal=_num(re.search(r"Subtotal:\s*" + AMOUNT, text)),
        tax=_num(re.search(r"Tax:\s*" + AMOUNT, text)),
        total=_num(re.search(r"(?:Total Due|Amount Due|TOTAL):\s*" + AMOUNT, text)),
    )