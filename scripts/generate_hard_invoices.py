"""Harder invoices: varied formats and layouts, half of them scanned (image-only PDFs)."""
import io
import json
import random
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from scripts.generate_invoices import build_invoice, make_vendor

N = 100
RAW = Path("data/raw_hard")
LABELS = Path("data/labels/labels_hard.json")
DATE_FMTS = ["%d %b %Y", "%B %d, %Y", "%d-%b-%Y", "%b %d, %Y"]
STYLES = ["footer_vendor", "stacked"]


def fmt_amt(x, cur):
    s = f"{x:,.2f}"
    if cur == "EUR":  # European style: 1.234,56
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def draw(inv, dates, style):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    cur = inv["currency"]
    amt = lambda x: f"{cur} {fmt_amt(x, cur)}"

    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, h - 60, "INVOICE" if style == "footer_vendor" else "Tax Invoice")
    c.setFont("Helvetica", 10)

    meta = [("Invoice number", inv["invoice_number"]), ("Invoice date", dates["invoice_date"]),
            ("Payment due", dates["due_date"]), ("Customer PO", inv["po_number"])]
    if style == "footer_vendor":
        y = h - 100
        for label, val in meta:
            c.drawString(50, y, f"{label}: {val}")
            y -= 14
    else:
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(w - 50, h - 60, inv["vendor_name"])
        c.setFont("Helvetica", 9)
        c.drawRightString(w - 50, h - 74, inv["vendor_address"][:60])
        c.setFont("Helvetica", 10)
        y = h - 120
        for label, val in meta:
            c.drawString(300, y, label)
            c.drawString(430, y, str(val))
            y -= 14

    c.drawString(50, h - 215, "Customer: Acme Holdings Inc.")
    ty = h - 260
    c.setFont("Helvetica-Bold", 10)
    cols = [50, 320, 380, 470]
    for x, name in zip(cols, ["Item", "Qty", "Price", "Line total"]):
        c.drawString(x, ty, name)
    c.line(50, ty - 4, w - 50, ty - 4)
    c.setFont("Helvetica", 10)
    ty -= 20
    for it in inv["line_items"]:
        c.drawString(cols[0], ty, it["description"])
        c.drawString(cols[1], ty, str(it["quantity"]))
        c.drawString(cols[2], ty, fmt_amt(it["unit_price"], cur))
        c.drawString(cols[3], ty, fmt_amt(it["amount"], cur))
        ty -= 16

    ty -= 10
    c.drawRightString(w - 50, ty, f"Subtotal: {amt(inv['subtotal'])}")
    c.drawRightString(w - 50, ty - 16, f"VAT / Tax: {amt(inv['tax'])}")
    c.setFont("Helvetica-Bold", 11)
    label = "Total" if style == "footer_vendor" else "Balance Due"
    c.drawRightString(w - 50, ty - 34, f"{label}: {amt(inv['total'])}")

    if style == "footer_vendor":
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, f"{inv['vendor_name']}  |  {inv['vendor_address'][:80]}")
    c.save()
    return buf.getvalue()


def write_scanned(pdf_bytes, path):
    """Rasterize, then add rotation, blur and noise, and save as an image-only PDF."""
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    pix = src[0].get_pixmap(dpi=150)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img = img.rotate(random.uniform(-2, 2), expand=False, fillcolor=(255, 255, 255))
    img = img.filter(ImageFilter.GaussianBlur(random.uniform(0.4, 0.9)))
    noise = Image.effect_noise(img.size, random.uniform(20, 40)).convert("RGB")
    img = Image.blend(img, noise, 0.07)
    jpg = io.BytesIO()
    img.save(jpg, "JPEG", quality=random.randint(55, 80))

    out = fitz.open()
    page = out.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=jpg.getvalue())
    out.save(str(path))


def main():
    random.seed(7)
    RAW.mkdir(parents=True, exist_ok=True)
    vendors = [make_vendor() for _ in range(20)]
    labels = []

    for i in range(1, N + 1):
        inv = build_invoice(random.choice(vendors))
        inv["invoice_number"] = random.choice([
            f"2026/{random.randint(1, 9999):04d}",
            f"A-{random.randint(10000, 99999)}",
            f"INV{random.randint(100000, 999999)}",
        ])
        inv["po_number"] = random.choice([
            str(random.randint(4500000000, 4599999999)),
            f"PO-{random.randint(10000, 99999)}",
        ])
        fmt = random.choice(DATE_FMTS)
        dates = {k: date.fromisoformat(inv[k]).strftime(fmt) for k in ("invoice_date", "due_date")}
        style = random.choice(STYLES)
        pdf = draw(inv, dates, style)

        file = f"hard_{i:04d}.pdf"
        scanned = random.random() < 0.5
        if scanned:
            write_scanned(pdf, RAW / file)
        else:
            (RAW / file).write_bytes(pdf)

        labels.append({
            "file": file, "layout": style, "scanned": scanned,
            "fields": {k: inv[k] for k in ("vendor_name", "currency", "invoice_number",
                                           "invoice_date", "due_date", "po_number",
                                           "subtotal", "tax", "total")},
            "line_items": inv["line_items"],
        })

    LABELS.write_text(json.dumps(labels, indent=2))
    print(f"Generated {len(labels)} hard invoices ({sum(l['scanned'] for l in labels)} scanned)")


if __name__ == "__main__":
    main()